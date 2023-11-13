from rest_framework.filters import SearchFilter, OrderingFilter, BaseFilterBackend
from django.db.models import Q
from pages.enums import PageFilter, PageOrderBy
from websites.models import WebsiteDomainType
from django.db.models import (
    Max,
)
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from pages.models import PublishedPageStatus
from pages.queries import (
    latest_published_date_for_custom_domain,
    latest_published_date_for_staging_domain,
)


class CustomFilter(BaseFilterBackend):
    filter_param = 'filter'
    filter_title = _('Filter')
    filter_description = _('A filter term.')

    def filter_queryset(self, request, queryset, view):
        filter = request.query_params.get('filter', None)
        if not filter:
            return queryset

        if filter == PageFilter.PUBLISHED.value:
            return queryset.filter(
                Q(
                    published_pages__date_created=latest_published_date_for_staging_domain,
                    published_pages__status=PublishedPageStatus.PUBLISHED,
                )
                | Q(
                    published_pages__date_created=latest_published_date_for_custom_domain,
                    published_pages__status=PublishedPageStatus.PUBLISHED,
                )
            )
        elif filter == PageFilter.UNPUBLISHED.value:
            return queryset.filter(
                Q(
                    published_pages__date_created=latest_published_date_for_staging_domain,
                    published_pages__status=PublishedPageStatus.UNPUBLISHED,
                )
                | Q(
                    published_pages__date_created=latest_published_date_for_custom_domain,
                    published_pages__status=PublishedPageStatus.UNPUBLISHED,
                )
            )
        elif filter == PageFilter.NOT_PUBLISHED.value:
            return queryset.filter(published_pages__isnull=True)
        else:
            return queryset


class CustomSearchFilter(SearchFilter):
    def filter_queryset(self, request, queryset, view):
        search = request.query_params.get('search', None)
        if search and search.lower() in 'home':
            return queryset.filter(
                Q(page__page_url__contains=search) | Q(page__page_url='')
            )
        if search:
            return queryset.filter(page__page_url__contains=search)
        return queryset


class CustomOrderingFilter(OrderingFilter):
    def filter_queryset(self, request, queryset, view):
        order_by = request.query_params.get('ordering', None)
        if order_by and order_by == PageOrderBy.PUBLISHED_STAGING_DOMAIN.value:
            queryset = (
                queryset.annotate(
                    latest_published_date=Max(
                        'published_pages__date_created',
                        filter=Q(
                            published_pages__domain__domain_type=WebsiteDomainType.DEFAULT_SUBDOMAIN,
                            published_pages__failed=False,
                            published_pages__status=PublishedPageStatus.PUBLISHED,
                            published_pages__date_created=latest_published_date_for_staging_domain,
                        ),
                    )
                )
            ).order_by(F('latest_published_date').desc(nulls_last=True))

        elif order_by and order_by == PageOrderBy.PUBLISHED_CUSTOM_DOMAIN.value:
            queryset = queryset.annotate(
                latest_published_date=Max(
                    'published_pages__date_created',
                    filter=Q(
                        published_pages__domain__domain_type=WebsiteDomainType.CUSTOM_ADDED,
                        published_pages__failed=False,
                        published_pages__status=PublishedPageStatus.PUBLISHED,
                        published_pages__date_created=latest_published_date_for_custom_domain,
                    ),
                )
            ).order_by(F('latest_published_date').desc(nulls_last=True))
        elif order_by and order_by == PageOrderBy.NOT_PUBLISHED_STAGING_DOMAIN.value:
            queryset = queryset.annotate(
                latest_published_date=Max(
                    'published_pages__date_created',
                    filter=Q(
                        published_pages__domain__domain_type=WebsiteDomainType.DEFAULT_SUBDOMAIN,
                        published_pages__failed=False,
                        published_pages__status=PublishedPageStatus.PUBLISHED,
                        published_pages__date_created=latest_published_date_for_staging_domain,
                    ),
                ),
            ).order_by(F('latest_published_date').asc(nulls_first=True))
        elif order_by and order_by == PageOrderBy.NOT_PUBLISHED_CUSTOM_DOMAIN.value:
            queryset = queryset.annotate(
                latest_published_date=Max(
                    'published_pages__date_created',
                    filter=Q(
                        published_pages__domain__domain_type=WebsiteDomainType.CUSTOM_ADDED,
                        published_pages__failed=False,
                        published_pages__status=PublishedPageStatus.PUBLISHED,
                        published_pages__date_created=latest_published_date_for_custom_domain,
                    ),
                ),
            ).order_by(F('latest_published_date').asc(nulls_first=True))
        return queryset
