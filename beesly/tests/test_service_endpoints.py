import unittest
import json

from beesly.views import app
from beesly.version import __app__, __version__


class ServiceEndpointsTests(unittest.TestCase):

    def setUp(self):
        app.config["DEV"] = False
        app.config["APP_NAME"] = __app__
        app.config["APP_VERSION"] = __version__

        self.app = app.test_client()

    def tearDown(self):
        pass

    def test_root_endpoint(self):
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, 200)

    def test_service_endpoint(self):
        resp = self.app.get('/service')
        self.assertEqual(resp.status_code, 200)

    def test_version_endpoint(self):
        resp = self.app.get('/service/version')
        self.assertEqual(resp.status_code, 200)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["version"], __version__)

    def test_health_endpoint(self):
        resp = self.app.get('/service/health')
        self.assertEqual(resp.status_code, 200)

        resp_body = json.loads(resp.data)
        self.assertEqual(resp_body["beesly"], 'OK')

    def test_nonexistant_endpoint(self):
        resp = self.app.get('/service/bar')
        self.assertEqual(resp.status_code, 404)
