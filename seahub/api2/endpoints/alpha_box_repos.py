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
from seahub.views import check_folder_permission

logger = logging.getLogger(__name__)

def get_my_repo_info(repo):
    repo_info = {
        "repo_id": repo.repo_id,
        "name": repo.repo_name,
        "size": repo.size,
        "starred": repo.starred,
        "last_modified": timestamp_to_isoformat_timestr(repo.last_modified),
        "encrypted": repo.encrypted,
    }

    return repo_info

def get_shared_in_repo_info(repo):
    repo_info = {
        "repo_id": repo.repo_id,
        "name": repo.repo_name,
        "size": repo.size,
        "starred": repo.starred,
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


class AlphaBoxRepo(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def put(self, request, repo_id):
        """ Star/unstar a repo

        Permission checking:
        1. User can view repo.
        """

        starred = request.data.get('starred', None)
        starred = starred.lower()
        if starred not in ('true', 'false'):
            error_msg = "starred should be 'true' or 'false'."
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if not check_folder_permission(request, repo_id, '/'):
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        username = request.user.username
        try:
            if starred == 'true':
                seafile_api.star_repo(repo_id, username)
            else:
                seafile_api.unstar_repo(repo_id, username)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response({'success': True})


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


class AlphaBoxReposSearch(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserRateThrottle,)

    def get_owned_repos_info(self, request):

        result = []
        username = request.user.username

        if is_org_context(request):
            org_id = request.user.org.org_id
            repos = seafile_api.get_org_owned_repo_list(org_id,
                    username, ret_corrupted=False, start=-1, limit=-1)
        else:
            repos = seafile_api.get_owned_repo_list(
                    username, ret_corrupted=False, start=-1, limit=-1)

        searched_name = request.GET.get('nameContains', '')
        for repo in repos:
            if searched_name.lower() not in repo.repo_name.lower():
                continue

            repo_info = get_my_repo_info(repo)
            repo_info['type'] = 'mine'
            result.append(repo_info)

        return result

    def get_shared_in_repos_info(self, request):

        result = []
        username = request.user.username

        shared_from = request.GET.get('shared_from', None)
        not_shared_from = request.GET.get('not_shared_from', None)

        if is_org_context(request):
            org_id = request.user.org.org_id
            if shared_from:
                repos = seafile_api.org_get_share_in_repo_list_with_sharer(org_id,
                        username, shared_from, negate=False, start=-1, limit=-1)
            elif not_shared_from:
                repos = seafile_api.org_get_share_in_repo_list_with_sharer(org_id,
                        username, not_shared_from, negate=True, start=-1, limit=-1)
            else:
                repos = seafile_api.get_org_share_in_repo_list(org_id,
                        username, start=-1, limit=-1)
        else:
            # TODO, not used currently
            repos = []

        searched_name = request.GET.get('nameContains', '')
        for repo in repos:
            if searched_name.lower() not in repo.repo_name.lower():
                continue

            repo_info = get_shared_in_repo_info(repo)
            repo_info['type'] = 'shared'
            result.append(repo_info)

        return result

    def get(self, request):
        """ Search repo by name

        Permission checking:
        1. all authenticated user can perform this action.
        """

        r_type = request.GET.get('type', '')
        if r_type and r_type not in ('mine', 'shared'):
            error_msg = "type should be 'mine' or 'shared'."
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        searched_name = request.GET.get('nameContains', '')
        if not searched_name:
            error_msg = 'nameContains invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        owned_repos_info = []
        shared_in_repos_info = []
        try:
            if not r_type:
                owned_repos_info = self.get_owned_repos_info(request)
                shared_in_repos_info = self.get_shared_in_repos_info(request)
            elif r_type.lower() == 'mine':
                owned_repos_info = self.get_owned_repos_info(request)
            elif r_type.lower() == 'shared':
                shared_in_repos_info = self.get_shared_in_repos_info(request)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response(owned_repos_info + shared_in_repos_info)
