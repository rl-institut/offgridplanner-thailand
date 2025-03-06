from django.core.management.base import BaseCommand, CommandError
from offgridplanner.projects.models import Project
from offgridplanner.users.models import User


class Command(BaseCommand):
    help = "Create a dummy a project "

    # def add_arguments(self, parser):
    #     parser.add_argument("proj_id", nargs="+", type=int)

    def handle(self, *args, **options):
        user, _ = User.objects.get_or_create(
            name="testUser",
            email="testUser@i.com",
            password="pbkdf2_sha256$216000$1KxHDBWRSd4x$ieFKUFRElRR0rIRW0oDHy9/Mdw54k8tn0ifl5Xgu7ps=",
            is_staff=False,
            is_active=True,
        )
        proj, _ = Project.objects.get_or_create(
            name="dummy", interest_rate=0.1, user=user
        )
        print(proj.id)
        proj.save()
