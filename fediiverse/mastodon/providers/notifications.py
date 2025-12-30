from ._base import BaseProvider


class NotificationsProvider(BaseProvider):
	async def get_unread_notifications_count(self) -> int:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v2" / "notifications" / "unread_count"
		)
		response.raise_for_status()
		return (await response.json())["count"]
