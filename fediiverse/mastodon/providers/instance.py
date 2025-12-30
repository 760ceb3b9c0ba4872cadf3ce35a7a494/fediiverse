from ._base import BaseProvider

from ..models.instance import InstanceV2, InstanceV1


class InstanceProvider(BaseProvider):
	async def get_instance_v2(self) -> InstanceV2:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v2" / "instance"
		)
		response.raise_for_status()
		data = await response.json()
		return InstanceV2(**data)

	async def get_instance_v1(self) -> InstanceV1:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v1" / "instance"
		)
		response.raise_for_status()
		data = await response.json()
		return InstanceV1(**data)
