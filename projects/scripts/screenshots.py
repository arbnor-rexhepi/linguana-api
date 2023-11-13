from app.external_services.background_services import generate_project_screenshot_async
from projects.selectors import get_all_projects


def sync_generate_project_screenshots():
    projects = get_all_projects()
    if len(projects) == 0:
        return
    for project in projects:
        generate_project_screenshot_async(project)
