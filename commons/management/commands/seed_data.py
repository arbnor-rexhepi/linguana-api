from django.core.management.base import BaseCommand
from faker import Faker
from projects.models import Project
from users.models import User
from websites.models import Website
from pages.models import Page


class Command(BaseCommand):
    help = 'This command used to apply seed data `python manage.py seed_data`'

    def handle(self, *args, **kwargs):
        fake = Faker()

        users = User.objects.all().order_by('date_joined')[::1][:10]

        # add fake projects
        for _ in range(100):
            name = fake.unique.catch_phrase()
            website_url = fake.unique.url()
            created_by = fake.random.choice(users)
            Project.objects.get_or_create(
                name=name,
                website_url=website_url,
                created_by=created_by,
            )

        projects = Project.objects.all()[::1]

        # add fake websites
        for _ in range(500):
            project = fake.random.choice(projects)
            domain = fake.unique.url()
            original_lang_code = 'en'
            content_url = fake.unique.url()
            Website.objects.get_or_create(
                project=project,
                domain=domain,
                original_lang_code=original_lang_code,
                content_url=content_url,
            )

        websites = Website.objects.all()[::1]

        # add fake pages
        for _ in range(1000):
            website = fake.random.choice(websites)
            page_url = fake.unique.url()
            Page.objects.get_or_create(website=website, page_url=page_url)
