from threading import Thread
from app.external_services.aws_services import takeScreenshot
from django.core.files.base import ContentFile
import logging
from app.external_services.parser_services import check_page_url_redirect


def generate_project_screenshot(project):
    try:
        screenshot = takeScreenshot(url=project.content_url)
        if screenshot:
            screenshot_name = f'{project.guid}-{project.domain}.png'
            screenshot = ContentFile(screenshot, screenshot_name)
            project.screenshot = screenshot
            project.save()
        return True
    except Exception as e:
        logging.error(
            f"""
                Failed to generate screenshot for project with
                guid:{project.guid}, url:{project.content_url}! Error:{repr(e)}
            """
        )
        return None


def generate_project_screenshot_async(project):
    try:
        project_content_url = check_page_url_redirect(project.content_url)
        if not project_content_url:
            return None
        thread = Thread(target=generate_project_screenshot, args=(project,))
        thread.start()
    except Exception as e:
        logging.error(
            f"""
                Failed to start a thread to generate screenshot for project with
                guid:{project.guid}, url:{project.content_url}
                ! Error:{repr(e)}
            """
        )
        return None
