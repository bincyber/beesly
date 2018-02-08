from distutils.spawn import find_executable
from distutils.util import strtobool
from urllib.parse import urlparse
import os
import os.path
import socket

from statsd import StatsClient

from beesly._logging import structured_log
from beesly.version import __app__, __version__


class ConfigError(Exception):
    """
    Exception raised when there is a configuration error.
    """


class StatsdConfig(object):
    """
    Manages statsd settings for exporting metrics.

    Attributes
    ----------
    prefix : string
       the prefix for metrics

    host : string
      the host of the statsd collector

    port : integer
      the UDP port of the statsd collector

    client : StatsClient object
      the initialized statsd client
    """
    def __init__(self):
        self.prefix = __app__.lower()
        self.host = os.environ.get("STATSD_HOST", "localhost")

        try:
            self.port = int(os.environ.get('STATSD_PORT', 8125))
        except ValueError:
            self.port = 8125

        # check that STATSD_HOST is a valid hostname or IPv4 address
        if self.host != "localhost":
            try:
                socket.gethostbyname(self.host)
            except:
                try:
                    socket.inet_aton(self.host)
                except:
                    structured_log(level='error', msg="Invalid value provided for STATSD_HOST. Defaulting to localhost")
                    self.host = "localhost"

        self.client = StatsClient(host=self.host, port=self.port, prefix=self.prefix)

        structured_log(level='info', msg=f"Statsd client configured to export metrics to {self.host}:{self.port}")


def initialize_config():
    """
    Initializes the application's configuration by reading settings from
    environment variables and validating them. Returns a dictionary containing
    application configuration if validation passes, otherwise ConfigError exception is raised.
    """
    settings = {}

    # ensure that all dependencies used exist
    dependencies = ['id']
    for binary in dependencies:
        if find_executable(binary) is None:
            structured_log(level='critical', msg="Failed to locate required dependency", dependency=binary)
            raise ConfigError()

    settings['APP_NAME']    = __app__
    settings['APP_VERSION'] = __version__
    settings['DEV']         = strtobool(os.environ.get("DEV", 'False'))

    settings["RATELIMIT_ENABLED"]       = strtobool(os.environ.get("RATELIMIT_ENABLED", 'True'))
    settings["RATELIMIT_STRATEGY"]      = os.environ.get("RATELIMIT_STRATEGY", 'fixed-window')
    settings["RATELIMIT_STORAGE_URL"]   = os.environ.get("RATELIMIT_STORAGE_URL", 'memory://')

    if not settings["RATELIMIT_ENABLED"]:
        structured_log(level='info', msg="Rate limiting disabled")

    if settings["RATELIMIT_ENABLED"]:

        rate_limit_strategies       = ['fixed-window', 'fixed-window-elastic-expiry', 'moving-window']
        rate_limit_storage_schemes  = ['memory', 'memcached', 'redis', 'rediss', 'redis+sentinel', 'redis_cluster']

        storage_scheme = urlparse(settings["RATELIMIT_STORAGE_URL"]).scheme

        if settings["RATELIMIT_STRATEGY"] not in rate_limit_strategies:
            structured_log(level='error', msg="Invalid value provided for RATELIMIT_STRATEGY")
            raise ConfigError()

        if storage_scheme not in rate_limit_storage_schemes:
            structured_log(level='error', msg="Invalid value provided for RATELIMIT_STORAGE_URL")
            raise ConfigError()

        if settings["RATELIMIT_STRATEGY"] == 'moving-window' and storage_scheme == 'memcached':
            structured_log(level='error', msg="Invalid value provided for RATELIMIT_STORAGE_URL. moving-window can't be used with memcached")
            raise ConfigError()

    # python-pam module allows specfiying which PAM service by name to authenticate against
    settings['PAM_SERVICE'] = os.environ.get("PAM_SERVICE", 'login')

    pam_file = f"/etc/pam.d/{settings['PAM_SERVICE']}"
    if not os.path.exists(pam_file):
        structured_log(level='error', msg=f"Invalid value provided for PAM_SERVICE. The pam configuration file '{pam_file}' does not exist")
        raise ConfigError()

    # configure JWT, by default it's disabled
    settings["JWT"] = False

    settings["JWT_MASTER_KEY"]  = os.environ.get('JWT_MASTER_KEY', None)
    settings["JWT_ALGORITHM"]   = os.environ.get('JWT_ALGORITHM', 'HS256')

    try:
        settings["JWT_VALIDITY_PERIOD"] = int(os.environ.get('JWT_VALIDITY_PERIOD', 900))
    except ValueError:
        settings["JWT_VALIDITY_PERIOD"] = 900

    if settings["JWT_MASTER_KEY"] is not None:
        if len(settings["JWT_MASTER_KEY"]) < 10 or len(settings["JWT_MASTER_KEY"]) > 64:
            structured_log(level='error', msg="Invalid value provided for JWT_MASTER_KEY. Must be between 10 - 64 characters")
            raise ConfigError()

        if settings["JWT_ALGORITHM"] not in ['HS256', 'HS384', 'HS512']:
            structured_log(level='error', msg="Invalid value provided for JWT_ALGORITHM. Defaulting to HS256")
            settings["JWT_ALGORITHM"] = 'HS256'

        settings["JWT"] = True
        settings["JWT_MASTER_KEY"] = bytes(settings["JWT_MASTER_KEY"], encoding='utf-8')

    return settings
