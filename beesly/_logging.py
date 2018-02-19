import logging

from beesly.version import __app__


class CustomLogFilter(logging.Filter):
    """
    Custom logging filter that adds the name of the application to each log.
    """
    APP = __app__

    def filter(self, record):
        record.app = CustomLogFilter.APP

        return True


def structured_log(level, msg, **kwargs):
    """
    Outputs structured, key-value log messages.

    Arguments
    ----------
    level : string
      the log level for the log, eg. info, warning, error, critical

    msg : string
      the message field in the log
    """
    level = level.upper()
    log_body = msg
    if kwargs:
        kv_pairs = ','.join([f'{k}={v}' for (k, v) in sorted(kwargs.items())]).rstrip('"') # trailing double quote is removed
        log_body += f'",{kv_pairs}' # double quote here closes the msg field

    app_logger_name = f'{__app__}.logger'
    app_logger_func = logging.getLogger(app_logger_name)

    app_logger = {
        'INFO': app_logger_func.info,
        'WARNING': app_logger_func.warning,
        'ERROR': app_logger_func.error,
        'CRITICAL': app_logger_func.critical
    }

    app_logger[level](log_body)
