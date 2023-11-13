from django.db import models
import uuid
from django_softdelete.models import SoftDeleteModel


class BaseModel(SoftDeleteModel):
    id = models.AutoField(primary_key=True)
    guid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    date_created = models.DateTimeField(auto_now_add=True, verbose_name='date created')
    date_updated = models.DateTimeField(auto_now=True, verbose_name='date updated')

    class Meta:
        abstract = True


class ServeSyncStatus(models.TextChoices):
    Pending = 'PENDING'
    Syncing = 'SYNCING'
    Failed = 'FAILED'
    Updated = 'UPDATED'


class MaintenanceStatus(models.TextChoices):
    UP = 'UP'
    DOWN = 'DOWN'


class MaintenanceMode(BaseModel):
    status = models.CharField(
        max_length=10,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.UP,
    )
    expected_down_time = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'maintenance_mode'
