from flask_restlib import RestLib
from flask_restlib.contrib.mongoengine import MongoEngineFactory

from .models import db


__all__ = ('db', 'rest')


rest = RestLib(
    factory=MongoEngineFactory()
)


import requests
from authlib.oauth2.rfc7662 import IntrospectTokenValidator as AbstractIntrospectTokenValidator


class IntrospectTokenValidator(AbstractIntrospectTokenValidator):
    def introspect_token(self, token_string: str) -> dict:
        print('Token ===>', token_string)
        resp = requests.post(
            'http://127.0.0.1:5000/oauth/introspect',
            data={'token': token_string, 'token_type_hint': 'access_token'},
            auth=('test', 'test')
        )
        resp.raise_for_status()
        return resp.json()


rest.resource_protector._token_validators.clear()
rest.resource_protector.register_token_validator(IntrospectTokenValidator())
