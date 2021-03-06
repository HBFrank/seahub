from seahub.notifications.models import (
    UserNotification, repo_share_msg_to_json, file_comment_msg_to_json,
    repo_share_to_group_msg_to_json, file_uploaded_msg_to_json,
    group_join_request_to_json, add_user_to_group_to_json, group_msg_to_json)

from seahub.test_utils import BaseTestCase


class UserNotificationTest(BaseTestCase):
    def test_format_file_comment_msg(self):
        detail = file_comment_msg_to_json(self.repo.id, self.file,
                                          self.user.username, 'test comment')
        notice = UserNotification.objects.add_file_comment_msg('a@a.com', detail)

        msg = notice.format_file_comment_msg()
        assert msg is not None
        assert 'new comment from user' in msg

    def test_format_file_uploaded_msg(self):
        upload_to = '/'
        detail = file_uploaded_msg_to_json('upload_msg', self.repo.id, upload_to)
        notice = UserNotification.objects.add_file_uploaded_msg('file@upload.com', detail)

        msg = notice.format_file_uploaded_msg()
        assert '/#common/lib/%(repo_id)s/%(path)s' % {'repo_id': self.repo.id,
                                                      'path': upload_to.strip('/')} in msg

    def test_format_repo_share_msg(self):
        detail = repo_share_msg_to_json('share@share.com', self.repo.id, '/', -1)
        notice = UserNotification.objects.add_repo_share_msg('to@to.com', detail)

        msg = notice.format_repo_share_msg()
        assert '/#common/lib/%(repo_id)s/%(path)s' % {'repo_id': self.repo.id,
                                                      'path': ''} in msg

    def test_format_repo_share_to_group_msg(self):
        detail = repo_share_to_group_msg_to_json('repo@share.com', self.repo.id, self.group.id, '/', -1)
        notice = UserNotification.objects.add_repo_share_to_group_msg('group@share.com', detail)

        msg = notice.format_repo_share_to_group_msg()
        assert '/#common/lib/%(repo_id)s/%(path)s' % {'repo_id': self.repo.id, 'path': ''} in msg
        assert '/#group/%(group_id)s/' % {'group_id': self.group.id} in msg

    def test_format_group_message_title(self):
        detail = group_msg_to_json(self.group.id, 'from@email.com', 'message')
        notice = UserNotification(to_user= 'to@user.com', msg_type='group_msg', detail=detail)
        msg = notice.format_group_message_title()
        assert '/#group/%(group_id)s/discussions/' % {'group_id': self.group.id} in msg

    def test_format_group_join_request(self):
        detail = group_join_request_to_json('group_join', self.group.id, 'join_request_msg')
        notice = UserNotification.objects.add_group_join_request_notice('group_join',
                                                                        detail=detail)
        msg = notice.format_group_join_request()
        assert '/#group/%(group_id)s/members/' % {'group_id': self.group.id} in msg

    def test_format_add_user_to_group(self):
        detail = add_user_to_group_to_json(self.user.username, self.group.id)
        notice = UserNotification.objects.set_add_user_to_group_notice(self.user.username,
                                                                       detail=detail)
        msg = notice.format_add_user_to_group()
        assert '/#group/%(group_id)s/' % {'group_id': self.group.id} in msg
