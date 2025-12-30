from typing import Optional, BinaryIO

import aiohttp

from ._base import BaseProvider
from ..models.media_attachment import MediaAttachment


class MediaProvider(BaseProvider):
	async def upload(
			self,
			*,
			file: BinaryIO,
			file_name: str,
			file_content_type: str,

			thumbnail: Optional[BinaryIO] = None,
			thumbnail_name: Optional[str] = None,
			thumbnail_content_type: Optional[str] = None,

			description: Optional[str] = None,
			focus: Optional[tuple[float, float]] = None
	):
		with aiohttp.MultipartWriter("form-data") as multipart:
			file_part = multipart.append(file, {"Content-Type": file_content_type})
			file_part.set_content_disposition("form-data", name="file", filename=file_name)

			if thumbnail:
				thumbnail_part = multipart.append(thumbnail, {"Content-Type": thumbnail_content_type})
				thumbnail_part.set_content_disposition("form-data", name="thumbnail")

			if description:
				description_part = multipart.append(description)
				description_part.set_content_disposition("form-data", name="description", filename=thumbnail_name)

			if focus:
				focus_part = multipart.append(f"{focus[0]},{focus[1]}")
				focus_part.set_content_disposition("form-data", name="focus")

			response = await self._session.request(
				method="POST",
				url=self._base_url / "v2" / "media",
				data=multipart
			)
			response.raise_for_status()
			return MediaAttachment(**(await response.json()))
