from typing import Any

from ._base import BaseProvider


class PreferencesProvider(BaseProvider):
	async def get_preferences(self) -> dict[str, Any]:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "preferences"
		)
		response.raise_for_status()
		return await response.json()
