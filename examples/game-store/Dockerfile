FROM kyzimaspb/flask:3.9-slim-buster

LABEL maintainer="Kirill Vercetti <office@kyzima-spb.com>"

RUN apt update

RUN set -x \
    && apt install -yq --no-install-recommends git \
    && apt-get clean  \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

#COPY ./requirements.txt /app/requirements.txt
COPY ./setup.py /app/setup.py

RUN pip install -q \
        --no-cache-dir \
        --disable-pip-version-check \
        --extra-index-url=https://test.pypi.org/simple \
        flask-restlib[sqla]

RUN pydep.sh

ADD ./ /app