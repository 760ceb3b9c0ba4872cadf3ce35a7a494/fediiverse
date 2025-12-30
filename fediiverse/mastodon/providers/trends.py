from typing import Optional

from ._base import BaseProvider
from ..models.status import Status


class TrendsProvider(BaseProvider):
	async def get_trending_statuses(
		self,
		limit: Optional[int] = None,
		offset: Optional[int] = None
	) -> list[Status]:
		params = {}
		if limit is not None:
			params["limit"] = limit
		if offset is not None:
			params["offset"] = offset

		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "trends" / "statuses" % params
		)
		response.raise_for_status()
		return [Status(**data) for data in await response.json()]
