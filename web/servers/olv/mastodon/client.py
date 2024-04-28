import asyncio

import aiohttp

from yarl import URL

from .providers.accounts import AccountsProvider
from .providers.instance import InstanceProvider
from .providers.statuses import StatusesProvider
from .providers.timelines import TimelinesProvider
from .providers.trends import TrendsProvider


class Client:
    def __init__(self, host: str | URL, token: str):
        self.base_url: URL = URL(host) / "api"

        self.session: aiohttp.ClientSession = aiohttp.ClientSession()
        self.session.headers["Authorization"] = f"Bearer {token}"

        self.timelines = TimelinesProvider(self)
        self.instance = InstanceProvider(self)
        self.statuses = StatusesProvider(self)
        self.accounts = AccountsProvider(self)
        self.trends = TrendsProvider(self)

    async def __aenter__(self):
        await self.session.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)
