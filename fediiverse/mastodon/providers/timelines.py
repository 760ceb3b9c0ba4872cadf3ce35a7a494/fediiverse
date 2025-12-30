from typing import Optional

from ._base import BaseProvider
from ..models.status import Status


class TimelinesProvider(BaseProvider):
	async def get_public_timeline(
		self,
		max_id: Optional[str] = None,
		since_id: Optional[str] = None,
		min_id: Optional[str] = None,
		limit: Optional[int] = None,
		local: bool = False,
		remote: bool = False,
		only_media: bool = False,
	) -> list[Status]:
		params = {
			"local": "true" if local else "false",
			"remote": "true" if remote else "false",
			"only_media": "true" if only_media else "false",
		}
		if max_id is not None:
			params["max_id"] = max_id
		if since_id is not None:
			params["since_id"] = since_id
		if min_id is not None:
			params["min_id"] = min_id
		if limit is not None:
			params["limit"] = str(limit)

		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "timelines" / "public" % params
		)
		response.raise_for_status()
		return [Status(**data) for data in await response.json()]

	async def get_home_timeline(
		self,
		max_id: Optional[str] = None,
		since_id: Optional[str] = None,
		min_id: Optional[str] = None,
		limit: Optional[int] = None
	) -> list[Status]:
		params = {}
		if max_id is not None:
			params["max_id"] = max_id
		if since_id is not None:
			params["since_id"] = since_id
		if min_id is not None:
			params["min_id"] = min_id
		if limit is not None:
			params["limit"] = limit

		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "timelines" / "home" % params
		)
		response.raise_for_status()
		return [Status(**data) for data in await response.json()]
