from django.db import migrations
from django.db import DEFAULT_DB_ALIAS, connections
from django.core.management import call_command
from django.db.migrations.loader import MigrationLoader
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    """
    Migrates to latest safe pre-deploy db schema. It ignores all migrations with postdeploy attribute behind.

    Pre-deploy migration requirements:
    * it only adds new tables and columns or extends old columns
    * it doesn’t remove anything and doesn’t limit old columns on anything
    * it should not add non-NULLable fields
    * it can be marked as safe by setting predeploy_safe attribute to True (if your are sure)
    * it can not be followed by migrations with postdeploy attribute
    """

    help = "Updates database schema if it's safe to do it before deploy."

    def add_arguments(self, parser):
        parser.add_argument(
            '--database', action='store', dest='database', default=DEFAULT_DB_ALIAS,
            help='Nominates a database to synchronize. Defaults to the "default" database.',
        )
        parser.add_argument(
            '--noinput', '--no-input', action='store_false', dest='interactive',
            help='Tells Django to NOT prompt the user for input of any kind.',
        )

    def handle(self, *args, **options):
        self.new_models = set()
        self.errors = []

        connection = connections[options['database']]
        loader = MigrationLoader(connection)

        plan = self.get_plan(loader)

        plan = self.rstrip_postdeploy_from_plan(plan)

        for m in plan:
            self.check_migration_safety(m)

        if self.errors:
            raise CommandError('\n' + '\n'.join(self.errors))

        if plan:
            call_command('migrate', plan[-1].app_label, plan[-1].name, **options)
        else:
            self.stdout.write('No pre-deploy migrations to apply.')

    def get_plan(self, loader):
        """Based on showmigrations.show_plan command"""

        # Load migrations from disk/DB
        graph = loader.graph
        targets = graph.leaf_nodes()
        plan = []
        seen = set()

        # Generate the plan
        for target in targets:
            for node in graph.forwards_plan(target):
                if node not in seen:
                    migration = graph.nodes[node]
                    if node not in loader.applied_migrations:
                        plan.append(migration)
                    seen.add(node)

        return plan

    def rstrip_postdeploy_from_plan(self, plan):
        while plan and getattr(plan[-1], 'postdeploy', False):
            plan = plan[:-1]
        return plan

    def check_migration_safety(self, m):
        if getattr(m, 'postdeploy', False):
            self.errors.append(f'Migration {m} should be run after deploy, but there are more migrations to go.')
            return

        if getattr(m, 'predeploy_safe', False):
            return

        for op in m.operations:
            self.check_operation_safety(m, op)

    def check_operation_safety(self, m, op):
        safe_ops = (
            migrations.AddIndex,
            migrations.RemoveIndex,
            migrations.AlterIndexTogether,
            migrations.AlterModelManagers,
            migrations.AlterModelOptions,
        )

        if isinstance(op, safe_ops):
            return

        if isinstance(op, migrations.AddField) and op.field.null:
            return

        if isinstance(op, migrations.CreateModel):
            self.new_models.add((m.app_label, op.name.lower()))
            return

        if hasattr(op, 'model_name') and (m.app_label, op.model_name) in self.new_models:
            return

        if isinstance(op, migrations.AlterUniqueTogether) and (m.app_label, op.name) in self.new_models:
            return

        self.errors.append(f'Operation {op} in {m} looks unsafe. Consider to set Migration.predeploy_safe if it is OK.')
