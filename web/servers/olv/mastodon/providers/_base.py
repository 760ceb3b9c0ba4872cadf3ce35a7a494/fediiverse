from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..client import Client


class BaseProvider:
    def __init__(self, client: Client):
        self._client = client

    @property
    def _session(self):
        return self._client.session

    @property
    def _base_url(self):
        return self._client.base_url
