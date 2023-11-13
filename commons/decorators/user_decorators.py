from websites.models import WebsiteLangVersion, WebsiteDomain
from projects.models import Project
from pages.models import PageLangVersion
from rest_framework.response import Response
from rest_framework import status
from commons.enums import OwnershipType
import functools


def check_user_ownership(argument):
    def inner_func(func):
        @functools.wraps(func)
        def check_and_call(self, request, *args, **kwargs):
            user = request.user
            guid = None
            if argument == OwnershipType.project:
                guid = kwargs['guid']
                project = Project.objects.filter(
                    guid=guid, created_by_id=user.id
                ).first()
                if not project:
                    return Response(
                        "You don't have right permissions to make the changes!.",
                        status=status.HTTP_403_FORBIDDEN,
                    )
            elif argument == OwnershipType.website_version:
                guid = kwargs['guid']
                website_version = WebsiteLangVersion.objects.filter(guid=guid).first()
                if (
                    not website_version
                    or website_version.website.project.created_by_id != user.id
                ):
                    return Response(
                        "You don't have right permissions to make the changes!.",
                        status=status.HTTP_403_FORBIDDEN,
                    )
            elif argument == OwnershipType.website_domain:
                guid = kwargs['guid']
                website_domain = WebsiteDomain.objects.filter(guid=guid).first()
                if (
                    not website_domain
                    or website_domain.website.project.created_by_id != user.id
                ):
                    return Response(
                        "You don't have right permissions to make the changes!.",
                        status=status.HTTP_403_FORBIDDEN,
                    )
            elif argument == OwnershipType.page_version:
                guid = kwargs['guid']
                page_version = PageLangVersion.objects.filter(guid=guid).first()
                if (
                    not page_version
                    or page_version.website_lang_version.website.project.created_by_id
                    != user.id
                ):
                    return Response(
                        "You don't have right permissions to make the changes!.",
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                return Response(
                    f'You are not the owner of this guid:{guid}.',
                    status=status.HTTP_403_FORBIDDEN,
                )
            return func(self, request, *args, **kwargs)

        return check_and_call

    return inner_func
