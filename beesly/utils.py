from hashlib import sha256
from distutils.spawn import find_executable
import re
import subprocess

from flask import request
import requests


def get_ec2_metadata():
    """
    Returns the following AWS EC2 metadata as a dictionary:
      * region
      * availability zone
      * image id
      * instance type
      * instance id
    """
    metadata_url = 'http://169.254.169.254/latest/dynamic/instance-identity/document/'

    resp = requests.get(metadata_url, timeout=0.250)

    json_body = resp.json()

    metadata = {
        'image_id': json_body.get('imageId'),
        'instance_type': json_body.get('instanceType'),
        'instance_id': json_body.get('instanceId'),
        'availability_zone': json_body.get('availabilityZone'),
        'region': json_body.get('region')
    }

    return metadata


def get_real_source_ip():
    """
    Returns the real source IP address of the HTTP request.
    """
    if 'X-Forwarded-For' in request.headers:
        return request.headers.getlist("X-Forwarded-For")[0].rpartition(' ')[-1]
    else:
        return request.environ['REMOTE_ADDR']


def get_request_ip_username():
    """
    Returns a unique key for rate limiting by extracting the username from the
    JSON request body, combining it with the remote address of the HTTP request
    and hashing it using SHA256.
    """
    request_json = request.get_json(force=True)

    rlimiting_key = get_real_source_ip()

    if request_json is not None:
        rlimiting_key += request_json.get('username', 'None')

    return sha256(rlimiting_key.encode('utf-8')).hexdigest()


def validate_username(username):
    """
    Checks if the username is valid and does not contain prohibited characters.
    Returns True if the username is valid, otherwise False.

    Arguments
    ----------
    username : string
      the username to check
    """
    regex = '^[a-zA-Z][-_.@a-z0-9]{1,32}$'
    if not re.match(regex, username):
        return False
    else:
        return True


def get_group_membership(username):
    """
    Returns a list of groups the user is a member of to support Role-Based Access Control.
    The `id` command is used because it reports all (POSIX) groups that the user
    is a member of including external groups from Identity Management systems (AD, IdM, FreeIPA).

    Arguments
    ----------
    username : string
      the username to get group membership for
    """
    exe = find_executable('id')
    process = subprocess.run([exe, '-Gn', username], stdout=subprocess.PIPE)
    groups = [group.decode('utf-8') for group in process.stdout.split()]
    groups.remove(username)
    return groups
