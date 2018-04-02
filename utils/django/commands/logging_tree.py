from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Prints out the loggers tree'

    def handle(self, *args, **options):
        import logging_tree
        logging_tree.printout()
