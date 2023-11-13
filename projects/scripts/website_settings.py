from websites.models import Website, WebsiteSettings
from websites.services import show_website_badge
from app.external_services.serve_services import (
    create_or_update_website_settings_in_serve,
)
import logging


def create_or_update_website_settings():
    logging.info('Started updating website settings')
    try:
        websites = Website.objects.all()
        for website in websites:
            WebsiteSettings.objects.update_or_create(
                website=website, defaults={'show_badge': show_website_badge(website)}
            )
            create_or_update_website_settings_in_serve(website=website)
    except Exception as E:
        logging.error(f'Website settings update failed, Error:{repr(E)}')
    logging.info('Finished updating website settings')
