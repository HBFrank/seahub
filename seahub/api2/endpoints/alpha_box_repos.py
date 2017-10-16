import logging

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from seaserv import seafile_api

from seahub.utils import is_org_context
from seahub.utils.timeutils import timestamp_to_isoformat_timestr

from seahub.api2.utils import api_error
from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication

logger = logging.getLogger(__name__)

def get_my_repo_info(repo):
    repo_info = {
        "repo_id": repo.repo_id,
        "name": repo.repo_name,
        "size": repo.size,
        "last_modified": timestamp_to_isoformat_timestr(repo.last_modified),
        "encrypted": repo.encrypted,
    }

    return repo_info

def get_shared_in_repo_info(repo):
    repo_info = {
        "repo_id": repo.repo_id,
        "name": repo.repo_name,
        "size": repo.size,
        "last_modified": timestamp_to_isoformat_timestr(repo.last_modified),
        "repo_owner": repo.user,
        "permission": repo.permission,
        "encrypted": repo.encrypted,
    }

    return repo_info


class AlphaBoxRepos(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """ List all my repos or repos shared to me

        Permission checking:
        1. all authenticated user can perform this action.
        """

        r_type = request.GET.get('type', 'mine')
        r_type = r_type.lower()
        if r_type not in ('mine', 'shared'):
            error_msg = "type should be 'mine' or 'shared'."
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        try:
            page = int(request.GET.get('page', '1'))
            per_page = int(request.GET.get('per_page', '100'))
        except ValueError:
            page = 1
            per_page = 100

        if page <= 0:
            error_msg = 'page invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if per_page <= 0:
            error_msg = 'per_page invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        start = (page - 1) * per_page
        limit = per_page

        result = []
        username = request.user.username
        if r_type == 'mine':
            try:
                if is_org_context(request):
                    org_id = request.user.org.org_id
                    repos = seafile_api.get_org_owned_repo_list(org_id,
                            username, ret_corrupted=False, start=start, limit=limit)
                else:
                    repos = seafile_api.get_owned_repo_list(
                            username, ret_corrupted=False, start=start, limit=limit)
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

            for repo in repos:
                repo_info = get_my_repo_info(repo)
                result.append(repo_info)

        if r_type == 'shared':

            shared_from = request.GET.get('shared_from', None)
            not_shared_from = request.GET.get('not_shared_from', None)

            try:
                if is_org_context(request):
                    org_id = request.user.org.org_id
                    if shared_from:
                        repos = seafile_api.org_get_share_in_repo_list_with_sharer(org_id,
                                username, shared_from, negate=False, start=start, limit=limit)
                    elif not_shared_from:
                        repos = seafile_api.org_get_share_in_repo_list_with_sharer(org_id,
                                username, not_shared_from, negate=True, start=start, limit=limit)
                    else:
                        repos = seafile_api.get_org_share_in_repo_list(org_id,
                                username, start=start, limit=limit)
                else:
                    # TODO, not used currently
                    repos = []
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

            for repo in repos:
                repo_info = get_shared_in_repo_info(repo)
                result.append(repo_info)

        return Response(result)


class AlphaBoxReposCount(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get(self, request):
        """ Get the number of all libraries that user can access.

        Permission checking:
        1. all authenticated user can perform this action.
        """

        r_type = request.GET.get('type', 'mine')
        r_type = r_type.lower()
        if r_type not in ('mine', 'shared'):
            error_msg = "type should be 'mine' or 'shared'."
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        repos_count = 0
        username = request.user.username

        if r_type == 'mine':
            try:
                if is_org_context(request):
                    org_id = request.user.org.org_id
                    repos_count = seafile_api.org_get_repo_num_by_owner(org_id,
                            username)
                else:
                    # TODO, not used currently
                    pass
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        if r_type == 'shared':

            shared_from = request.GET.get('shared_from', None)
            not_shared_from = request.GET.get('not_shared_from', None)

            try:
                if is_org_context(request):
                    org_id = request.user.org.org_id
                    if shared_from:
                        repos_count = seafile_api.org_get_share_repo_num_with_sharer(org_id,
                                username, shared_from, negate=False)
                    elif not_shared_from:
                        repos_count = seafile_api.org_get_share_repo_num_with_sharer(org_id,
                                username, not_shared_from, negate=True)
                    else:
                        repos_count = seafile_api.org_get_share_repo_num_with_sharer(org_id,
                                username, '', negate=True)
                else:
                    # TODO, not used currently
                    pass
            except Exception as e:
                logger.error(e)
                error_msg = 'Internal Server Error'
                return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        result = {
            'count': repos_count,
        }

        return Response(result)
