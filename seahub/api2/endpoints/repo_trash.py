# Copyright (c) 2012-2016 Seafile Ltd.
import stat
import logging
import posixpath

from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from seahub.api2.throttling import UserRateThrottle
from seahub.api2.authentication import TokenAuthentication
from seahub.api2.utils import api_error

from seahub.signals import clean_up_repo_trash
from seahub.utils import normalize_file_path
from seahub.utils.timeutils import timestamp_to_isoformat_timestr
from seahub.utils.repo import get_repo_owner
from seahub.views import check_folder_permission

from seahub.repo_trash.models import TrashCleanedItems

from seaserv import seafile_api
from pysearpc import SearpcError

logger = logging.getLogger(__name__)

class RepoTrash(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, )
    throttle_classes = (UserRateThrottle, )

    def get_item_info(self, trash_item):

        item_info = {
            'parent_dir': trash_item.basedir,
            'obj_name': trash_item.obj_name,
            'deleted_time': timestamp_to_isoformat_timestr(trash_item.delete_time),
            'scan_stat': trash_item.scan_stat,
            'commit_id': trash_item.commit_id,
        }

        if stat.S_ISDIR(trash_item.mode):
            is_dir = True
        else:
            is_dir = False

        item_info['is_dir'] = is_dir
        item_info['size'] = trash_item.file_size if not is_dir else ''
        item_info['obj_id'] = trash_item.obj_id if not is_dir else ''

        return item_info

    def get(self, request, repo_id, format=None):
        """ Return deleted files/dirs of a repo/folder

        Permission checking:
        1. all authenticated user can perform this action.
        """

        # argument check
        path = request.GET.get('path', '/')

        # resource check
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        try:
            dir_id = seafile_api.get_dir_id_by_path(repo_id, path)
        except SearpcError as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        if not dir_id:
            error_msg = 'Folder %s not found.' % path
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        if check_folder_permission(request, repo_id, path) is None:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            show_days = int(request.GET.get('show_days', '0'))
        except ValueError:
            show_days = 0

        if show_days < 0:
            error_msg = 'show_days invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        scan_stat = request.GET.get('scan_stat', None)
        try:
            # a list will be returned, with at least 1 item in it
            # the last item is not a deleted entry, and it contains an attribute named 'scan_stat'
            deleted_entries = seafile_api.get_deleted(repo_id,
                    show_days, path, scan_stat)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        scan_stat = deleted_entries[-1].scan_stat
        more = True if scan_stat is not None else False

        items = []
        if len(deleted_entries) > 1:
            entries_without_scan_stat = deleted_entries[0:-1]

            # sort entry by delete time
            entries_without_scan_stat.sort(lambda x, y : cmp(y.delete_time,
                                                             x.delete_time))

            for item in entries_without_scan_stat:
                item_info = self.get_item_info(item)
                items.append(item_info)

        # filter out cleaned file/folder
        cleaned_path = []
        try:
            trash_cleaned_items = TrashCleanedItems.objects.get_items_by_repo(repo_id)
        except Exception as e:
            logger.error(e)
            trash_cleaned_items = []

        for item in trash_cleaned_items:
            cleaned_path.append(item.path)

        filtered_items = []
        for item in items:

            obj_full_path = posixpath.join(
                    item['parent_dir'], item['obj_name'])
            obj_full_path = normalize_file_path(obj_full_path)

            if obj_full_path in cleaned_path:
                continue
            else:
                filtered_items.append(item)

        result = {
            'data': filtered_items,
            'more': more,
            'scan_stat': scan_stat,
        }

        return Response(result)

    def delete(self, request, repo_id, format=None):
        """ Clean library's trash.

        Permission checking:
        1. only repo owner can perform this action.
        """

        # argument check
        try:
            keep_days = int(request.data.get('keep_days', 0))
        except ValueError:
            error_msg = 'keep_days invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # resource check
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        username = request.user.username
        repo_owner = get_repo_owner(request, repo_id)
        if username != repo_owner:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            seafile_api.clean_up_repo_history(repo_id, keep_days)
            org_id = None if not request.user.org else request.user.org.org_id
            clean_up_repo_trash.send(sender=None, org_id=org_id, operator=username, repo_id=repo_id, repo_name=repo.name, days=keep_days)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response({'success': True})


class RepoTrashItem(APIView):

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, )
    throttle_classes = (UserRateThrottle, )

    def delete(self, request, repo_id, format=None):
        """ Delete file/folder from library's trash.

        Permission checking:
        1. only repo owner can perform this action.
        """

        # argument check
        path = request.data.get('path', None)
        if not path:
            error_msg = 'path invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        # as we don't know `path` patameter stands for a file or folder
        # we always right strip `/` from it.
        path = normalize_file_path(path)

        # resource check
        repo = seafile_api.get_repo(repo_id)
        if not repo:
            error_msg = 'Library %s not found.' % repo_id
            return api_error(status.HTTP_404_NOT_FOUND, error_msg)

        # permission check
        username = request.user.username
        repo_owner = get_repo_owner(request, repo_id)
        if username != repo_owner:
            error_msg = 'Permission denied.'
            return api_error(status.HTTP_403_FORBIDDEN, error_msg)

        try:
            TrashCleanedItems.objects.add_item(repo_id, path)
        except Exception as e:
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        return Response({'success': True})
