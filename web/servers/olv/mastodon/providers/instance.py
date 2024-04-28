from typing import Optional

from ._base import BaseProvider
from pydantic import BaseModel

from ..models.instance import Instance
from ..models.status import Status


class InstanceProvider(BaseProvider):
	async def get_instance(self) -> Instance:
		response = await self._session.request(
			method="GET",
			url=self._base_url / "v2" / "instance"
		)
		response.raise_for_status()
		data = await response.json()
		return Instance(**data)
