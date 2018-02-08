import socket
import time
import traceback

from flask import Flask, request, jsonify, escape
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pam import pam
from jose import jwt, JWTError
from nacl.encoding import URLSafeBase64Encoder
from nacl.hash import blake2b
import nacl.utils
import psutil

from beesly._logging import structured_log
from beesly.config import StatsdConfig
from beesly.utils import get_ec2_metadata, get_request_ip_username, get_real_source_ip
from beesly.utils import validate_username, get_group_membership


app = Flask(__name__, static_folder=None, static_url_path=None)

rlimiter = Limiter(key_func=get_remote_address, headers_enabled=True)

statsd = StatsdConfig()


@app.route("/", methods=["GET"])
@rlimiter.limit("10/second")
def index():
    """
    Returns information about this microservice such as name, version,
    what endpoints are available and which HTTP methods they support.
    """
    response_body = {
        "hostname": socket.gethostname(),
        "app": app.config['APP_NAME'],
        "version": app.config['APP_VERSION'],
        "routes": []
    }

    for rule in app.url_map.iter_rules():
        response_body['routes'].append({
            'endpoint': rule.rule,
            'methods': sorted(rule.methods)
        })

    return jsonify(response_body), 200


@app.route("/service", methods=["GET"])
@rlimiter.limit("10/second")
def service_info():
    """
    Returns information about this microservice such as name, version,
    and metadata about the server it is running on.
    """

    total_memory_mb = "{} MB".format(psutil.virtual_memory().total / (1024 * 1024))
    system_uptime = round((time.time() - psutil.boot_time()), 3)
    app_uptime = round((time.time() - psutil.Process().create_time()), 3)

    response_body = {
        'app': {
            'name': app.config['APP_NAME'],
            'version': app.config['APP_VERSION'],
            'uptime': app_uptime
        },
        'system': {
            "hostname": socket.gethostname(),
            'processors': psutil.cpu_count(),
            'memory': total_memory_mb,
            'uptime': system_uptime,
        }
    }

    try:
        response_body["aws"] = get_ec2_metadata()
    except Exception:
        pass

    return jsonify(response_body), 200


@app.route("/service/version", methods=["GET"])
@rlimiter.limit("10/second")
def service_version():
    """
    Returns the name and version of this microservice.
    """
    response_body = {
        'app': app.config['APP_NAME'],
        'version': app.config['APP_VERSION'],
    }

    return jsonify(response_body), 200


@app.route("/service/health", methods=["GET"])
@rlimiter.limit("10/second")
def service_health():
    """
    Health check endpoint for load balancers and monitoring systems.
    """
    app_name = app.config['APP_NAME']

    response_body = {
        app_name: "OK"
    }

    return jsonify(response_body), 200


@app.route("/auth", methods=["POST"])
@rlimiter.limit("10/second", methods=["POST"], key_func=get_request_ip_username)
def auth_endpoint():
    """
    Authenticates users using PAM.
    If authentication is successful, returns a list of groups the user is a member of.
    Returns a short-lived JSON Web Token if JWT_MASTER_KEY is set.
    """
    if request.method == 'POST':
        request_json = request.get_json(force=True, cache=False)

        username = request_json.get('username', None)
        password = request_json.get('password', None)

        if username is None or password is None:
            return jsonify(message="No username or password provided"), 400

        sanitized_username = str(escape(username))

        if not validate_username(sanitized_username):
            structured_log(level='warning', msg="Invalid username provided", user=f"'{sanitized_username}'")
            return jsonify(message="Invalid username provided"), 400

        pam_service = app.config['PAM_SERVICE']

        with statsd.client.timer("pam_auth"):
            if pam().authenticate(sanitized_username, password, service=pam_service):
                authenticated = True
                auth_message = "Authentication successful"
                statsd.client.incr("auth_success")
            else:
                authenticated = False
                auth_message = "Authentication failed"
                statsd.client.incr("auth_failed")

        structured_log(level='info', msg=auth_message, user=f"'{sanitized_username}'")

        if authenticated:
            groups = get_group_membership(sanitized_username)

            token = None

            if app.config["JWT"]:
                issuer      = app.config['APP_NAME']
                issue_time  = time.time()
                expiry_time = issue_time + app.config['JWT_VALIDITY_PERIOD']
                subject     = sanitized_username.encode('utf-8')

                # generate a unique salt for each JWT, needs to be encoded to include as a claim
                salt = URLSafeBase64Encoder.encode(nacl.utils.random(12))

                claims = {
                    "iss": issuer,
                    "iat": issue_time,
                    "exp": expiry_time,
                    "sub": sanitized_username,
                    "groups": groups,
                    "x": salt.decode('utf-8')
                }

                master_key  = app.config["JWT_MASTER_KEY"]
                algorithm   = app.config["JWT_ALGORITHM"]

                # generate a unique secret key for each JWT
                secret_key = blake2b(b'', key=master_key, salt=salt, person=subject).decode('utf-8')

                token = jwt.encode(claims=claims, key=secret_key, algorithm=algorithm)
                statsd.client.incr("jwt_generated")

            return jsonify(message=f"{auth_message}", auth=True, groups=groups, jwt=token), 200
        else:
            return jsonify(message=f"{auth_message}", auth=False), 401


@app.route("/renew", methods=["POST"])
@rlimiter.limit("1/second", methods=["POST"], key_func=get_request_ip_username)
def renew_endpoint():
    """
    Renews a JWT that has not expired.
    """
    if request.method == 'POST':

        if not app.config["JWT"]:
            return jsonify(message="JWT renewal is not enabled"), 501

        request_json = request.get_json(force=True, cache=False)

        token       = request_json.get('jwt', None)
        username    = request_json.get('username', None)

        if token is None or username is None:
            return jsonify(message="No JWT or username provided"), 400

        sanitized_username = str(escape(username))

        if not validate_username(sanitized_username):
            structured_log(level='warning', msg="Invalid username provided", user=f"'{sanitized_username}'")
            return jsonify(message="Invalid username provided"), 400

        try:
            claims = jwt.get_unverified_claims(token)
        except JWTError:
            return jsonify(message="Invalid JWT"), 400

        try:
            subject = claims["sub"].encode('utf-8')
            salt    = claims["x"].encode('utf-8')
        except KeyError:
            return jsonify(message="Invalid claims in JWT"), 401

        if sanitized_username != claims["sub"]:
            return jsonify(message="Invalid subject in JWT claim"), 400

        master_key  = app.config["JWT_MASTER_KEY"]
        algorithm   = app.config["JWT_ALGORITHM"]
        issuer      = app.config['APP_NAME']

        # jwt.decode() requires secret_key to be a str, so it must be decoded
        secret_key = blake2b(b'', key=master_key, salt=salt, person=subject).decode('utf-8')

        # exception is raised if token has expired, signature verification fails, etc.
        try:
            payload = jwt.decode(token=token, key=secret_key, algorithms=algorithm, issuer=issuer)
        except Exception as err:
            structured_log(level='info', msg="Failed to renew JWT", error=err)
            return jsonify(message="Failed to renew invalid JWT"), 401

        issue_time  = time.time()
        expiry_time = issue_time + app.config['JWT_VALIDITY_PERIOD']

        salt = URLSafeBase64Encoder.encode(nacl.utils.random(12))

        payload['iat']  = issue_time
        payload['exp']  = expiry_time
        payload['x']    = salt.decode('utf-8')

        # compute a new secret key for the regenerated JWT
        new_secret_key  = blake2b(b'', key=master_key, salt=salt, person=subject).decode('utf-8')
        new_token       = jwt.encode(claims=payload, key=new_secret_key, algorithm=algorithm)

        statsd.client.incr("jwt_renewed")
        structured_log(level='info', msg="JWT successfully renewed", user="'{}'".format(sanitized_username))
        return jsonify(message="JWT successfully renewed", jwt=new_token), 200


@app.route("/verify", methods=["POST"])
@rlimiter.limit("500/second")
def verify_endpoint():
    """
    Verifies if a JWT is valid.
    """
    if request.method == 'POST':

        if not app.config["JWT"]:
            return jsonify(message="JWT verification is not enabled"), 501

        request_json = request.get_json(force=True, cache=False)

        token = request_json.get('jwt', None)

        if token is None:
            return jsonify(message="No JWT provided"), 400

        try:
            claims = jwt.get_unverified_claims(token)
        except:
            return jsonify(message="Invalid JWT"), 400

        master_key  = app.config["JWT_MASTER_KEY"]
        algorithm   = app.config["JWT_ALGORITHM"]
        issuer      = app.config['APP_NAME']

        try:
            subject = claims["sub"].encode('utf-8')
            salt    = claims["x"].encode('utf-8')
        except KeyError:
            return jsonify(message="Invalid claims in JWT", valid=False), 401

        # jwt.decode() requires secret_key to be a str, so it must be decoded
        secret_key = blake2b(b'', key=master_key, salt=salt, person=subject).decode('utf-8')

        # exception is raised if token has expired, signature verification fails, etc.
        try:
            jwt.decode(token=token, key=secret_key, algorithms=algorithm, issuer=issuer)
        except Exception as err:
            structured_log(level='info', msg="Failed to verify JWT", error=err)
            return jsonify(message="Failed to verify JWT", valid=False), 401

        statsd.client.incr("jwt_verified")
        structured_log(level='info', msg="JWT successfully verified", user=f"'{subject}'")
        return jsonify(message="JWT successfully verified", valid=True), 200


@app.after_request
def after_request(resp):
    """
    Adds HTTP Headers to the response

    Arguments
    ----------
    resp : flask.Response object
      the Flask response object
    """
    resp.headers['Cache-Control'] = 'no-cache'

    if app.config['DEV']:
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        resp.headers['Access-Control-Allow-Headers'] = 'Origin, X-Requested-With, Content-Type, Accept'

        source_ip = get_real_source_ip()

        structured_log(
            level='info',
            msg="HTTP Request",
            method=request.method,
            uri=request.path,
            status=resp.status_code,
            src_ip=source_ip,
            protocol=request.environ['SERVER_PROTOCOL'],
            user_agent=request.environ.get('HTTP_USER_AGENT', '-')
        )

    return resp


@app.errorhandler(404)
def http_404_handler(err):
    """
    Catches any 404 errors and responds with a custom error message.
    """
    return jsonify(error="The requested endpoint does not exist"), 404


@app.errorhandler(429)
def rate_limit_handler(err):
    """
    Custom error message returned when rate limits are exceeded.
    """
    return jsonify(error=f"Rate limit exceeded {err.description}"), 429


@app.errorhandler(Exception)
def exception_handler(err):
    """
    Catches any exceptions raised by this microservice and responds with
    HTTP 500 and a custom error message.
    """
    tb = traceback.format_exc()
    formatted_traceback = ' '.join(tb.splitlines()[1:]).strip()

    structured_log(level='error', msg="Encountered an exception", traceback=formatted_traceback)
    return jsonify(error="The application failed to handle the request"), 500
