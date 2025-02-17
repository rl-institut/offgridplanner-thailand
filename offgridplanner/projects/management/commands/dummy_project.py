from django.core.management.base import BaseCommand, CommandError
from offgridplanner.projects.models import Project


class Command(BaseCommand):
    help = "Create a dummy a project "

    # def add_arguments(self, parser):
    #     parser.add_argument("proj_id", nargs="+", type=int)

    def handle(self, *args, **options):
        proj,_ = Project.objects.get_or_create(name="dummy", interest_rate=0.1)
        print(proj.id)
        proj.save()
