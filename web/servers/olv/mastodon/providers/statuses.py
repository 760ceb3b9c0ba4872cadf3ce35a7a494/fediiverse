from typing import Optional, Literal

from ._base import BaseProvider
from pydantic import BaseModel

from ..models.status import Status


class StatusesProvider(BaseProvider):
	async def reblog(
			self,
			status_id: str,
			visibility: Optional[Literal["public", "unlisted", "private"]] = None
	) -> Status:
		data = {}

		if visibility is not None:
			data["visibility"] = visibility

		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "statuses" / status_id / "reblog"
		)
		response.raise_for_status()
		return Status(**(await response.json()))

	async def unreblog(self, status_id: str) -> Status:
		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "statuses" / status_id / "unreblog"
		)
		response.raise_for_status()
		return Status(**(await response.json()))

	async def bookmark(self, status_id: str) -> Status:
		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "statuses" / status_id / "bookmark"
		)
		response.raise_for_status()
		return Status(**(await response.json()))

	async def unbookmark(self, status_id: str) -> Status:
		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "statuses" / status_id / "unbookmark"
		)
		response.raise_for_status()
		return Status(**(await response.json()))

	async def favourite(self, status_id: str) -> Status:
		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "statuses" / status_id / "favourite"
		)
		response.raise_for_status()
		return Status(**(await response.json()))

	async def unfavourite(self, status_id: str) -> Status:
		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "statuses" / status_id / "unfavourite"
		)
		response.raise_for_status()
		return Status(**(await response.json()))
