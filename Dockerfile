# builds a Docker container image
# https://docs.docker.com/engine/reference/builder/
#
# docker build -t beesly:latest .

FROM python:3.6-slim

LABEL APP="beesly"
LABEL MAINTAINER="@bincyber"
LABEL URL="http://github.com/bincyber/beesly"

COPY ./requirements.txt /tmp/requirements.txt

RUN set -ex && apt-get update -qq \
    && apt-get -y --no-install-recommends install build-essential libffi-dev \
    && pip install -r /tmp/requirements.txt --no-cache-dir --disable-pip-version-check \
    && apt-get purge -y --auto-remove build-essential libffi-dev \
    && apt-get -y autoremove \
    && rm -rf /var/lib/apt/lists/* \
    && rm -f /var/log/dpkg.log \
    && rm -rf /usr/share/doc \
    && rm -rf /usr/src/python ~/.cache \
    && find /usr/local -depth -type f -a -name '*.pyc' -exec rm -rf '{}' \;

ADD . /opt/app

WORKDIR /opt/app

USER nobody

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/gunicorn", "-c", "gconfig.py", "--preload", "-w", "4", "-b", "0.0.0.0:8000", "serve:app"]
