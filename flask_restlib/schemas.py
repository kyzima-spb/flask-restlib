from __future__ import annotations
import typing as t

from flask import current_app
import marshmallow as ma
from marshmallow.types import StrSequenceOrSet


class RestlibMixin:
    class Opts:
        def __init__(self, meta: object, *args: t.Any, **kwargs: t.Any) -> None:
            # self.links = getattr(meta, 'links', {})
            self._dump_only: StrSequenceOrSet = ()
            self._load_only: StrSequenceOrSet = ()
            super().__init__(meta, *args, **kwargs)  # type: ignore

        @property
        def dump_only(self) -> set[str]:
            config = current_app.config
            dump_only = {
                config['RESTLIB_ID_FIELD'],
                config['RESTLIB_CREATED_FIELD'],
                config['RESTLIB_UPDATED_FIELD'],
            }
            dump_only.update(config['RESTLIB_DUMP_ONLY'])
            dump_only.update(self._dump_only)
            return dump_only

        @dump_only.setter
        def dump_only(self, value: StrSequenceOrSet) -> None:
            self._dump_only = value

        @property
        def load_only(self) -> set[str]:
            load_only = set()
            load_only.update(current_app.config['RESTLIB_LOAD_ONLY'])
            load_only.update(self._load_only)
            return load_only

        @load_only.setter
        def load_only(self, value: StrSequenceOrSet) -> None:
            self._load_only = value


class RestlibSchemaOpts(RestlibMixin.Opts, ma.SchemaOpts):
    pass


class RestlibSchema(ma.Schema):
    OPTIONS_CLASS = RestlibSchemaOpts
