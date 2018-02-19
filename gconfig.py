# gunicorn config file

import logging
import logging.config
import os
import os.path
import sys

app_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, app_path)

from beesly.version import __app__

app_logger = f'{__app__}.logger'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'key_value_format': {
            'format': '{"timestamp":"%(asctime)s.%(msecs).03d","loglevel":"%(levelname)s","app":"%(app)s","pid":"%(process)d","message":"%(message)s"}',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'filters': {
        'customFilter': {
            '()': 'beesly._logging.CustomLogFilter'
        }
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'key_value_format',
            'stream': 'ext://sys.stdout'
        },
        'null': {
            'class': 'logging.NullHandler'
        }
    },
    'loggers': {
        '': {
            'handlers': ['null']
        },
        app_logger: {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
            'filters': ['customFilter']
        },
        'gunicorn.error': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
            'filters': ['customFilter']
        },
    },
}

logging.config.dictConfig(LOGGING)

def on_starting(server):

    # remove gunicorn's stream handler to prevent duplicate logs
    gunicornLogger = logging.getLogger('gunicorn.error')
    gunicornLogger.handlers.pop(1)
    return
