import unittest
import os

from beesly import create_app
from beesly.config import initialize_config, ConfigError, StatsdConfig


class ConfigTests(unittest.TestCase):

    def setUp(self):
        env_vars = [
            "DEV"
            "JWT_ALGORITHM",
            "JWT_MASTER_KEY",
            "JWT_VALIDITY_PERIOD",
            "PAM_SERVICE",
            "RATELIMIT_ENABLED",
            "RATELIMIT_STORAGE_URL",
            "RATELIMIT_STRATEGY",
            "STATSD_HOST",
            "STATSD_PORT",
        ]

        for i in env_vars:
            try:
                del os.environ[i]
            except:
                pass

    def tearDown(self):
        pass

    def test_swagger_ui_enabled(self):
        os.environ["DEV"] = "True"

        app = create_app().test_client()

        resp = app.get('/service/docs/index.html')
        self.assertEqual(resp.status_code, 200)
        del app

    def test_swagger_ui_disabled(self):
        app = create_app().test_client()

        resp = app.get('/service/docs/index.html')
        self.assertEqual(resp.status_code, 404)

    def test_invalid_pam_service(self):
        os.environ["PAM_SERVICE"] = "blah"

        with self.assertRaises(ConfigError):
            initialize_config()

    def test_invalid_rate_limit_strategy(self):
        os.environ["RATELIMIT_STRATEGY"] = "blah"

        with self.assertRaises(ConfigError):
            initialize_config()

    def test_invalid_rate_limit_storage_backend(self):
        os.environ["RATELIMIT_STORAGE_URL"] = "blah"

        with self.assertRaises(ConfigError):
            initialize_config()

    def test_invalid_rate_limit_strategy_storage_memcached(self):
        os.environ["RATELIMIT_STRATEGY"] = "moving-window"
        os.environ["RATELIMIT_STORAGE_URL"] = "memcached://localhost:11211"

        with self.assertRaises(ConfigError):
            initialize_config()

    def test_invalid_jwt_master_key(self):
        os.environ["JWT_MASTER_KEY"] = "blah"

        with self.assertRaises(ConfigError):
            initialize_config()

        del os.environ["JWT_MASTER_KEY"]

    def test_invalid_jwt_validity_period(self):
        os.environ["JWT_VALIDITY_PERIOD"] = "blah"

        settings = initialize_config()

        self.assertEqual(settings["JWT_VALIDITY_PERIOD"], 900)

    def test_invalid_jwt_algorithm(self):
        os.environ["JWT_ALGORITHM"] = "blah"
        os.environ["JWT_MASTER_KEY"] = "passwordpassword"

        settings = initialize_config()

        self.assertEqual(settings["JWT_ALGORITHM"], "HS256")

    def test_statsd_config(self):
        os.environ["STATSD_HOST"] = "A B C D"
        os.environ["STATSD_PORT"] = "abcd"

        statsd = StatsdConfig()

        self.assertTrue(statsd.client)
        self.assertEqual(statsd.host, "localhost")
        self.assertEqual(statsd.port, 8125)
        self.assertEqual(statsd.prefix, "beesly")


class CreateAppTest(unittest.TestCase):

    def setUp(self):
        os.environ["RATELIMIT_ENABLED"] = "False"

    def tearDown(self):
        del os.environ["RATELIMIT_ENABLED"]

    def test_create_app(self):
        self.assertIsNotNone(create_app())
