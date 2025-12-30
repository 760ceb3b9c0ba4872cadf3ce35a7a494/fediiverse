from typing import Optional

import aiohttp
from yarl import URL

from .providers.accounts import AccountsProvider
from .providers.apps import AppsProvider
from .providers.instance import InstanceProvider
from .providers.media import MediaProvider
from .providers.notifications import NotificationsProvider
from .providers.oauth import OAuthProvider
from .providers.preferences import PreferencesProvider
from .providers.statuses import StatusesProvider
from .providers.timelines import TimelinesProvider
from .providers.trends import TrendsProvider


class Client:
    def __init__(self, host: str | URL, token: Optional[str] = None):
        self.host_url: URL = URL(host)
        self.base_url: URL = self.host_url / "api"

        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(
                connect=30,  # max. 30 seconds for connection from pool
                sock_connect=15,  # max. 15 seconds for socket to connect
                sock_read=120,  # max. 2 minutes for data to be read
            )
        )
        if token:
            self.set_token(token)

        self.notifications = NotificationsProvider(self)
        self.preferences = PreferencesProvider(self)
        self.timelines = TimelinesProvider(self)
        self.instance = InstanceProvider(self)
        self.statuses = StatusesProvider(self)
        self.accounts = AccountsProvider(self)
        self.trends = TrendsProvider(self)
        self.media = MediaProvider(self)
        self.oauth = OAuthProvider(self)
        self.apps = AppsProvider(self)

    def set_token(self, token: str):
        self.session.headers["Authorization"] = f"Bearer {token}"

    async def __aenter__(self):
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
