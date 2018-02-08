# beesly

[![Python](https://img.shields.io/badge/Python-3.6-yellow.svg)](#)
[![GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl.html)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](#)
[![Build Status](https://travis-ci.org/bincyber/beesly.svg?branch=master)](https://travis-ci.org/bincyber/beesly)
[![Coverage Status](https://coveralls.io/repos/github/bincyber/beesly/badge.svg?branch=master)](https://coveralls.io/github/bincyber/beesly?branch=master)


beesly is a microservice for authenticating users with PAM.

It provides an alternative method for authenticating and authorizing users' access to internal applications and services. Support for custom PAM services facilitates the reuse of existing integrations (SSSD) with directory servers (Active Directory, IdM, FreeIPA, OpenLDAP, etc.) and third party services (Duo Security). Group membership is returned for authenticated users allowing the addition of Role-Based Access Control for custom applications and services without the need to learn the intricacies of LDAP or Kerberos.

beesly was developed in Python 3.6 using the Flask microframework.


### Features

* Authenticate users with custom PAM services
* Role-Based Access Control (RBAC)
* Integration with Duo Security for 2-Factor Authentication (2FA)
* short-lived JSON Web Tokens (JWT)
* Rate limits to prevent abuse


## Prerequisites

[Pipenv](https://docs.pipenv.org/) is used to manage dependencies.

beesly requires superuser privileges to authenticate users when running in its default configuration because it uses the PAM login service which uses the `pam_unix.so` PAM module. This module adds a 2 second delay for failed authentications which can be disabled by using the nodelay option. It's encouraged to use a custom PAM service that does not use this module.

If using a custom PAM service, the configuration file should be placed in `/etc/pam.d` with `0644` permissions. See `examples/beesly.pam` for an example of a custom PAM service that uses SSSD and does not require superuser privileges.

[Flask-Limiter](https://flask-limiter.readthedocs.io/en/stable/) is used to implement rate limits. It can use in-memory, Redis, or Memcached as a storage backend.

## Usage

Run beesly using gunicorn:

    $ gunicorn -c gconfig.py -b '127.0.0.1:8000' -w 4 serve:app

For production deployment, run gunicorn behind nginx and use TLS.

### Examples

Authenticating a user:

    $ curl -X POST http://127.0.0.1:8000/auth -d '{"username":"dwight.schrute@dundermifflin.com", "password":"BearsBeetsBattlestarGalactica"}'

    {
      "auth": true,
      "groups": [
        "Sales",
        "Assistant_Regional_Managers"
      ],
      "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiZWVz...",
      "message": "Authentication successful"
    }

A successful authentication will return the groups that the user is a member of facilitating RBAC.

If Duo Security 2FA is configured, the user will have to acknowledge a push notification for the authentication to succeed.

The payload of the generated JWT contains the following claims:

    {
      'exp': 1489344336.296496,
      'groups': [
        "Sales",
        "Assistant_Regional_Managers"
      ],
      'iat': 1489343436.296496,
      'iss': 'beesly',
      'sub': 'dwight.schrute@dundermifflin.com',
      'x': '2soDlgCPC0RFuxR0'
    }

Note: a JWT is returned only when `JWT_MASTER_KEY` is configured.


Renewing an existing JWT that has not expired:

    $ curl -X POST http://127.0.0.1:8000/renew -d '{"username":"dwight.schrute@dundermifflin.com","jwt":"2NzUuMjEyMzAyLCJncm91cHMiOm51bGwsInN1Yi..."}'

    {
      "jwt": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJiZWvR...",
      "message": "JWT successfully renewed"
    }


Verifying the validity of a JWT:

    $ curl -X POST http://127.0.0.1:8000/verify -d '{"jwt":"2NzUuMjEyMzAyLCJncm91cHMiOm51bGwsInN1Yi..."}'

    {
      "message": "JWT successfully verified",
      "valid": true
    }

Note: `/renew` and `/verify` endpoints are only available if `JWT_MASTER_KEY` is configured.


Retrieving information about the running application:

    $ curl http://127.0.0.1:8000/service

    {
      "app": {
        "name": "beesly",
        "uptime": 9,
        "version": "0.1.0"
      },
      "aws": {
        "availability_zone": "us-west-2b",
        "image_id": "ami-d2c924b2",
        "instance_id": "i-0ef224f23818bd413",
        "instance_type": "t2.micro",
        "region": "us-west-2"
      },
      "system": {
        "hostname": "ip-172-31-36-157",
        "memory": "991 MB",
        "processors": 1,
        "uptime": 10647
      }
    }

Note: EC2 metadata is returned only when running on AWS EC2.


Monitoring the health of the application:

    $ curl http://127.0.0.1:8000/service/health

    {
      "beesly": "OK"
    }


### API Documentation

[Swagger UI](http://swagger.io/swagger-ui/) is integrated into beesly and available at `/service/docs/index.html` when running in `DEV` mode.


### Configuration

The following environment variables are used to modify the running configuration of this app:

| Variable | Type | Required | Default Value | Explanation
| -------- | -------- | -------- | -------- | --------
| DEV | Boolean | No | False | Set to True to enable debug logging and Swagger UI.
| PAM_SERVICE | String | No | login | The name of the PAM service to authenticate users with.
| JWT_MASTER_KEY | String | No | | The master key to use when generating JSON Web Tokens.<br />Must be between 10 - 64 characters in length.
| JWT_ALGORITHM | String | No | HS256 | The HMAC algorithm to use when generating JWTs.<br /> One of: <br />* `HS256` <br />* `HS384` <br />* `HS512`
| JWT_VALIDITY_PERIOD | Interger | No | 900 | The validity period in seconds for generated JWTs.
| STATSD_HOST | String | No | localhost | The hostname or IP address of the statsd collector.
| STATSD_PORT | Integer | No | 8125 | The UDP port of the statsd collector.
| RATELIMIT_ENABLED | Boolean | No | True | Set to False to disable rate limiting.
| RATELIMIT_STRATEGY | String | No | fixed-window | The rate limiting strategy to use.<br />One of: <br />* `fixed-window` <br />* `fixed-window-elastic-expiry` <br />* `moving-window`
| RATELIMIT_STORAGE_URL | String | No | memory:// | The URL for the storage backend used for rate limiting.<br />Refer to [limits](http://limits.readthedocs.io/en/latest/storage.html#storage-scheme) documentation for correct syntax.


Note: The `moving-window` rate limiting strategy can only be used with `in-memory` or `Redis` storage.


### Integrating with Duo Security

beesly can integrate with [Duo Security](https://duo.com/docs/duounix) to provide 2-factor authentication
using the `pam_duo.so` PAM module.

Create a custom PAM service:

    $ sudo vim /etc/pam.d/beesly

    auth    required      pam_env.so
    auth    requisite     pam_duo.so
    auth    sufficient    pam_unix.so nodelay
    auth    required      pam_deny.so

Configure `duo_unix` to send push notifications to the user's phone:

    $ sudo vim /etc/duo/pam_duo.conf

    ; Duo Unix config
    ; https://duo.com/docs/duounix
    [duo]
    ikey=
    skey=
    host=
    failmode=secure
    autopush=yes
    prompts=1
    https_timeout=2

Users will have to acknowledge the push notification for authentication to succeed.


### JSON Web Tokens

beesly can optionally return short-lived JSON Web Tokens upon successful user authentication. To add JWT support, a secret master key must be set via the `JWT_MASTER_KEY` environment variable. It must be between 10 - 64 characters in length.

blake2b key derivation function from [pynacl](https://pynacl.readthedocs.io/en/latest/hashing/#key-derivation) is used to create a unique signing key for each generated token:

    master_key = app.config["JWT_MASTER_KEY"]
    unique_salt = nacl.encoding.URLSafeBase64Encoder.encode(nacl.utils.random(12))

    signing_key = blake2b(b'', key=master_key, salt=unique_salt, person=username)

By default, each JWT is valid for 15 minutes. JWTs can be renewed by sending a POST request to `/renew` with the payload containing the username and their valid token. JWTs can be verified by sending a POST request to `/verify` with the payload containing the token.


### Metrics

The Python [statsd](https://github.com/jsocol/pystatsd) client is used to export application metrics with the prefix `beesly`.

The following metrics are exported:

| Name | Type | Explanation
| -------- | -------- | --------
| pam_auth | Meter | Time taken by PAM to authenticate a user
| auth_success | Counter | User authentication succeeded
| auth_failed | Counter | User authentication failed
| jwt_generated | Counter | a JWT was successfully generated
| jwt_renewed | Counter | a JWT was successfully renewed
| jwt_verified | Counter | a JWT was successfully verified

See `examples/telegraf.conf` for how to configure [telegraf](https://github.com/influxdata/telegraf) as a [statsd](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/statsd) collector sending metrics to [influxdb](https://github.com/influxdata/influxdb).


### Testing

[nose2](http://nose2.readthedocs.io/en/latest/) is used for testing. Tests are located in `beesly/tests`.

The tests require valid credentials to a local user to execute correctly. Credentials for this user can be set using environment variables:

    $ export TEST_USERNAME=example
    $ export TEST_PASSWORD=helloworld

To run the test suite:

    $ sudo make test
