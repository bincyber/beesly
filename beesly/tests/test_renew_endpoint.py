import unittest
import json
import os

from jose import jwt

from beesly.views import app
from beesly.version import __app__


class RenewEndpointTests(unittest.TestCase):

    def setUp(self):
        app.config["APP_NAME"] = __app__
        app.config["DEV"] = False
        app.config["PAM_SERVICE"] = "login"
        app.config["JWT"] = True
        app.config["JWT_MASTER_KEY"] = "passwordpassword"
        app.config["JWT_VALIDITY_PERIOD"] = 10
        app.config["JWT_ALGORITHM"] = "HS256"

        self.app = app.test_client()

        self.username = os.environ.get("TEST_USERNAME", "vagrant")
        self.password = os.environ.get("TEST_PASSWORD", "vagrant")

        req_body = json.dumps(dict(username=self.username, password=self.password))
        resp = self.app.post('/auth', data=req_body, content_type='application/json')

        self.token = json.loads(resp.data)["jwt"]

    def tearDown(self):
        pass

    def test_renew_endpoint_disabled(self):
        app.config["JWT"] = False

        resp = self.app.post('/renew')
        self.assertEqual(resp.status_code, 501)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'JWT renewal is not enabled')

    def test_renew_endpoint_success(self):
        req_body = json.dumps(dict(jwt=self.token, username=self.username))
        resp = self.app.post('/renew', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 200)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'JWT successfully renewed')

    def test_renew_endpoint_failure(self):

        claims = jwt.get_unverified_claims(self.token)
        new_token = jwt.encode(claims=claims, key='notthepassword', algorithm=app.config["JWT_ALGORITHM"])

        req_body = json.dumps(dict(jwt=new_token, username=self.username))
        resp = self.app.post('/renew', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 401)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Failed to renew invalid JWT')

    def test_renew_endpoint_invalid_subject(self):
        req_body = json.dumps(dict(jwt=self.token, username="INVALID"))
        resp = self.app.post('/renew', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Invalid subject in JWT claim')

    def test_renew_endpoint_invalid_username(self):
        req_body = json.dumps(dict(jwt=self.token, username=self.username + " dak298n"))
        resp = self.app.post('/renew', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Invalid username provided')

    def test_renew_endpoint_invalid_token(self):
        req_body = json.dumps(dict(jwt="INVALID", username=self.username))
        resp = self.app.post('/renew', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Invalid JWT')

    def test_renew_endpoint_invalid_claims(self):

        claims = jwt.get_unverified_claims(self.token)
        del claims["sub"]
        new_token = jwt.encode(claims=claims, key='notthepassword', algorithm=app.config["JWT_ALGORITHM"])

        req_body = json.dumps(dict(jwt=new_token, username=self.username))
        resp = self.app.post('/renew', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 401)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'Invalid claims in JWT')

    def test_renew_endpoint_missing_token(self):
        req_body = json.dumps(dict(username=self.username))
        resp = self.app.post('/renew', data=req_body, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["message"], 'No JWT or username provided')
