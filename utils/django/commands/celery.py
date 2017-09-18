import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def run_from_argv(self, argv):
        from celery import maybe_patch_concurrency
        from celery.bin.celery import main

        settings_module = os.environ['DJANGO_SETTINGS_MODULE']
        project_module = settings_module.split('.', 1)[0]
        argv = ['celery', '-A', project_module] + argv[2:]

        if 'multi' not in argv:
            maybe_patch_concurrency(argv)

        main(argv)
