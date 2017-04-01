import unittest
import json
import os

from beesly.views import app
from beesly.version import __app__


class AuthEndpointTests(unittest.TestCase):

    def setUp(self):
        app.config["APP_NAME"] = __app__
        app.config["DEV"] = False
        app.config["PAM_SERVICE"] = "login"
        app.config["JWT"] = True
        app.config["JWT_MASTER_KEY"] = "passwordpassword"
        app.config["JWT_VALIDITY_PERIOD"] = 5
        app.config["JWT_ALGORITHM"] = "HS256"

        self.app = app.test_client()

        self.username = os.environ.get("TEST_USERNAME", "vagrant")
        self.password = os.environ.get("TEST_PASSWORD", "vagrant")

    def tearDown(self):
        pass

    def test_auth_endpoint_success(self):
        req_body = json.dumps(dict(username=self.username, password=self.password))
        resp = self.app.post('/auth', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Authentication successful')

    def test_auth_endpoint_failure(self):
        req_body = json.dumps(dict(username=self.username, password=self.password + "nc8awdaw"))
        resp = self.app.post('/auth', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 401)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Authentication failed')

    def test_auth_endpoint_invalid_username(self):
        req_body = json.dumps(dict(username=self.username + " d@.-0z", password=self.password))
        resp = self.app.post('/auth', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Invalid username provided')

    def test_auth_endpoint_missing_parameters(self):
        req_body = json.dumps(dict(username=self.username))
        resp = self.app.post('/auth', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'No username or password provided')
