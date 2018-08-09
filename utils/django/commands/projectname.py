from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Prints out project module name'

    def handle(self, *args, **options):
        from django.conf import settings
        print(settings.PROJECT_NAME)
