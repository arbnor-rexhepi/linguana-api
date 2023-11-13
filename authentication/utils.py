from django.conf import settings


def get_only_allowed_emails():
    return [email.strip().lower() for email in settings.ALLOWED_EMAILS]


def is_email_allowed(email):
    if not get_only_allowed_emails():
        return True
    if email.strip().lower() not in get_only_allowed_emails():
        return False
    return True
