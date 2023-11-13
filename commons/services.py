from commons.models import MaintenanceMode


def get_or_none(class_model, **kwargs):
    try:
        return class_model.objects.get(**kwargs)
    except class_model.MultipleObjectsReturned as e:
        print(e)
    except class_model.DoesNotExist:
        return None


def get_maintenance_mode():
    return MaintenanceMode.objects.last()
