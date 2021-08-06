from __future__ import annotations

from authlib.integrations.flask_oauth2 import current_token

from .core import RestLib
from .globals import (
    current_restlib,
    authorization_server,
    F,
    query_adapter,
    resource_manager
)
