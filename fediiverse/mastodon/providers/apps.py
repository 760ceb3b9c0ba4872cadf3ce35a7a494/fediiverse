from typing import Optional

from ._base import BaseProvider

from ..models.application import Application


class AppsProvider(BaseProvider):
	async def create_application(
		self,
		*,
		client_name: str,
		redirect_uris: list[str] | str,
		scopes: Optional[list[str]] = None,
		website: Optional[str] = None
	) -> Application:
		data = {
			"client_name": client_name,
			"redirect_uris": redirect_uris
		}
		if scopes:
			data["scopes"] = " ".join(scopes)
		if website:
			data["website"] = website

		response = await self._session.request(
			method="POST",
			url=self._base_url / "v1" / "apps",
			data=data
		)
		response.raise_for_status()
		data = await response.json()
		return Application(**data)
