from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone
from commons.models import BaseModel, SoftDeleteModel
from django.db.models import Sum
from django.conf import settings
import uuid

from users.consts import USER_PROFILE_IMAGES_FOLDER_NAME


class UserManager(BaseUserManager):
    def _create_user(self, email, password, is_staff, is_superuser, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        now = timezone.now()
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            is_staff=is_staff,
            is_active=True,
            is_superuser=is_superuser,
            last_login=now,
            date_joined=now,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        return self._create_user(email, password, False, False, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        user = self._create_user(email, password, True, True, **extra_fields)
        user.save(using=self._db)
        return user


class UserType(models.TextChoices):
    FREE = 'FREE'
    LIFETIME_USER = 'LIFETIME_USER'
    UNLIMITED = 'UNLIMITED'


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteModel):
    email = models.EmailField(max_length=254, unique=True)
    guid = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=254, null=True, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    type = models.CharField(
        max_length=100, choices=UserType.choices, default=UserType.FREE
    )

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    def get_absolute_url(self):
        return '/users/%i/' % (self.pk)

    class Meta:
        db_table = 'user'

    @property
    def remaining_credits(self):
        return self.credits.aggregate(Sum('ai_credits')).get('ai_credits__sum', 0) or 0

    @property
    def verified_email(self):
        email_address = self.emailaddress_set.get(email=self.email)
        if email_address:
            return email_address.verified
        return None

    @property
    def email_confirmation_expire_days(self):
        email = self.emailaddress_set.get(email=self.email)
        if not email.verified:
            expire_date = timezone.timedelta(
                days=settings.ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS
            )
            return abs((self.date_joined + expire_date - timezone.now()).days)
        return 0

    @property
    def deactivated_account(self):
        if self.is_active:
            return False
        return True

    @property
    def picture(self):
        try:
            return (
                self.socialaccount_set.filter(user_id=self.id)
                .first()
                .extra_data['picture']
                or ''
            )
        except:  # noqa
            return ''

    @property
    def full_name(self):
        try:
            return (
                self.socialaccount_set.filter(user_id=self.id)
                .first()
                .extra_data['name']
                or ''
            )
        except:  # noqa
            return ''

    def get_user_firebase_token(self):
        try:
            return self.firebase.token
        except:  # noqa
            return None


class UserCreditsSource(models.TextChoices):
    MANUALLY = 'MANUALLY'
    SUBSCRIPTION = 'SUBSCRIPTION'
    CREDITS = 'CREDITS'


class UserCredits(BaseModel):
    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE, related_name='credits'
    )
    ai_credits = models.IntegerField(default=0)
    source = models.CharField(
        max_length=50,
        choices=UserCreditsSource.choices,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = 'user_credits'
        verbose_name_plural = 'User Credits'

    @property
    def balance(self):
        return (
            UserCredits.objects.filter(
                date_created__lte=self.date_created, user=self.user
            )
            .aggregate(Sum('ai_credits'))
            .get('ai_credits__sum', 0)
            or 0
        )


class UserProfile(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    firstname = models.CharField(max_length=200, null=True, blank=True)
    lastname = models.CharField(max_length=200, null=True, blank=True)
    picture = models.ImageField(
        null=True, blank=True, upload_to=USER_PROFILE_IMAGES_FOLDER_NAME
    )

    class Meta:
        db_table = 'user_profile'


class UserFirebaseToken(BaseModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='firebase',
    )
    token = models.CharField(max_length=500)

    class Meta:
        db_table = 'user_firebase_token'
