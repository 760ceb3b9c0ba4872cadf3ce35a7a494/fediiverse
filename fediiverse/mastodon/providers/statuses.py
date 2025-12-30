from typing import Optional, Literal

from ._base import BaseProvider
from ..models.context import Context
from ..models.status import Status, StatusVisibility


class StatusesProvider(BaseProvider):
	async def post(
			self,
			*,
			status: str,
			media_ids: Optional[list[str]] = None,
			# poll
			in_reply_to_id: Optional[str] = None,
			sensitive: bool = False,
			spoiler_text: Optional[str] = None,
			visibility: StatusVisibility,
			language: Optional[str] = None,
			# scheduled_at
	):
		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "statuses",
			json={
				"status": status,
				"media_ids": media_ids,
				"in_reply_to_id": in_reply_to_id,
				"sensitive": sensitive,
				"spoiler_text": spoiler_text,
				"visibility": visibility.value,
				"language": language
			}
		)
		response.raise_for_status()
		return Status(**(await response.json()))

	async def get(self, status_id: str) -> Status:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "statuses" / status_id
		)
		response.raise_for_status()
		return Status(**(await response.json()))

	async def get_context(self, status_id: str) -> Context:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "statuses" / status_id / "context"
		)
		response.raise_for_status()
		return Context(**(await response.json()))

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

	async def delete(self, status_id: str) -> None:
		response = await self._session.request(
			method="DELETE",
			url=self._base_url / "v1" / "statuses" / status_id
		)
		response.raise_for_status()
		# return Status(**(await response.json()))  # fixme bc there are additional fields in this response!
