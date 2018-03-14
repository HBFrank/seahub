import json
from django.core.urlresolvers import reverse
from seahub.test_utils import BaseTestCase

class RepoViewTest(BaseTestCase):

    def setUp(self):
        self.user_name = self.user.username
        self.admin_name = self.admin.username
        self.url = reverse('api-v2.1-alpha-box-repo', args=[self.repo.id])

    def tearDown(self):
        self.remove_repo()

    def test_star_repo(self):

        self.login_as(self.user)

        data = {"starred": 'true'}
        resp = self.client.put(self.url, json.dumps(data),
                'application/json')
        self.assertEqual(200, resp.status_code)

    def test_can_not_star_repo_with_invalid_repo_permission(self):

        self.login_as(self.admin)

        data = {"starred": 'true'}
        resp = self.client.put(self.url, json.dumps(data),
                'application/json')
        self.assertEqual(403, resp.status_code)

    def test_unstar_repo(self):

        self.login_as(self.user)

        data = {"starred": 'false'}
        resp = self.client.put(self.url, json.dumps(data),
                'application/json')
        self.assertEqual(200, resp.status_code)

    def test_can_not_unstar_repo_with_invalid_repo_permission(self):

        self.login_as(self.admin)

        data = {"starred": 'true'}
        resp = self.client.put(self.url, json.dumps(data),
                'application/json')
        self.assertEqual(403, resp.status_code)
