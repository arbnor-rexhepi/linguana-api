from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from users.services import send_email_to_admin_users
from app.external_services.mailerlite_services import send_mailer_lite_subscriber
from commons.utils import get_client_ip
from users.utils import get_first_last_name
from threading import Thread


def handle_user_signed_up(request, user):
    send_email_to_admin_users(signup_user=user)
    name, last_name = get_first_last_name(user.full_name)
    send_mailer_lite_subscriber(user.email, name, last_name, get_client_ip(request))


@receiver(user_signed_up)
def user_signed_up_(request, user, **kwargs):
    t = Thread(target=handle_user_signed_up, args=(request, user))
    t.start()
