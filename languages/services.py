from languages.models import Language


def get_languages(guid_ids):
    return Language.objects.filter(guid__in=guid_ids)


def get_language_ids(guid_ids):
    return Language.objects.filter(guid__in=guid_ids).values_list('id', flat=True)
