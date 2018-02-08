import sys
import os.path

from beesly._logging import structured_log
from beesly.config import ConfigError, initialize_config
from beesly.views import app, rlimiter


def create_app():
    """
    Initializes the Flask application.
    """

    structured_log(level='info', msg="Starting beesly...")

    try:
        settings = initialize_config()
    except ConfigError:
        structured_log(level='critical', msg="Failed to load configuration. Exiting...")
        sys.exit(4)

    # enable Swagger UI if running in DEV mode
    if settings["DEV"]:
        app.static_folder = os.path.dirname(os.path.realpath(__file__)) + "/swagger-ui"
        app.add_url_rule("/service/docs/<path:filename>", endpoint="/service/docs", view_func=app.send_static_file)

    app.config.update(settings)
    structured_log(level='info', msg="Successfully loaded configuration")

    rlimiter.init_app(app)

    return app
