FROM kyzimaspb/sphinx

RUN pip install -q \
        --no-cache-dir \
        --disable-pip-version-check \
        --extra-index-url=https://test.pypi.org/simple \
            flask-restlib \
            flask-restlib[sqla] \
            flask-restlib[mongoengine]

ADD ./ /docs/source/
