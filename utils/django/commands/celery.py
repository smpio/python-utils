import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def run_from_argv(self, argv):
        from celery.bin.celery import main
        argv = ['celery', '-A', self.get_celery_module_name()] + argv[2:]
        main(argv)

    def get_celery_module_name(self):
        settings_module = os.environ['DJANGO_SETTINGS_MODULE']
        project_module = settings_module.split('.', 1)[0]
        return project_module + '.celery'
