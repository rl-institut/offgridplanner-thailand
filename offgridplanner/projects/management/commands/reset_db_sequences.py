from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    # This command is needed once after restoring the database data, so that the counters for instance creation are up
    # to date. The database commands to be executed can be seen with python manage.py sqlsequencereset: https://docs.djangoproject.com/en/5.2/ref/django-admin/#sqlsequencereset
    help = "Reset the primary key sequences to max(id)+1"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for model in apps.get_models():
                if not model._meta.managed or not model._meta.auto_field:  # noqa: SLF001
                    continue

                table = model._meta.db_table  # noqa: SLF001
                query = (
                    f"SELECT setval(pg_get_serial_sequence('\"{table}\"', 'id'), "  # noqa: S608
                    f'coalesce(max("id"), 1), max("id") IS NOT null) FROM "{table}";'
                )
                cursor.execute(query)

                self.stdout.write(self.style.SUCCESS(f"✅ Reset sequence for {table}"))
