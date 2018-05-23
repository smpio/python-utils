import os
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def run_from_argv(self, argv):
        from gunicorn.app.wsgiapp import run
        sys.argv = self.get_argv(argv)
        sys.exit(run())

    def get_argv(self, argv):
        return ['gunicorn'] + argv[2:] + [self.get_wsgi_module_name()]

    def get_wsgi_module_name(self):
        settings_module = os.environ['DJANGO_SETTINGS_MODULE']
        project_module = settings_module.split('.', 1)[0]
        return project_module + '.wsgi'
