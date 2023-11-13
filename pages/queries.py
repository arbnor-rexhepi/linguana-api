from django.db.models import (
    Subquery,
    OuterRef,
)
from websites.models import WebsiteDomainType
from pages.models import PublishedPageVersionStatus


latest_published_date_for_staging_domain = Subquery(
    PublishedPageVersionStatus.objects.filter(
        page_version=OuterRef('pk'),
        domain__domain_type=WebsiteDomainType.DEFAULT_SUBDOMAIN,
        failed=False,
    )
    .order_by('-date_created')
    .values('date_created')[:1]
)

latest_published_date_for_custom_domain = Subquery(
    PublishedPageVersionStatus.objects.filter(
        page_version=OuterRef('pk'),
        domain__domain_type=WebsiteDomainType.CUSTOM_ADDED,
        failed=False,
    )
    .order_by('-date_created')
    .values('date_created')[:1]
)
