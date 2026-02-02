import asyncio
import datetime
import io
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Literal, Optional

import aiohttp
from PIL import Image
from aiohttp import ClientResponseError
from cryptography.fernet import Fernet
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, HttpUrl
from yarl import URL

from ...storage import get_config, FediiverseMode

config = get_config()
hosts = config.hosts

http: aiohttp.ClientSession
fernet: Fernet = Fernet(config.secrets.temporal_secret_key)

MAX_CONTENT_LENGTH = 8_000_000  # maximum file size to attempt to proxy


pfp_mask_32 = Image.open(Path(__file__).parent / "pfp-mask-32.png").convert("L")
blank_image_32 = Image.new("RGBA", (32, 32), (255, 255, 255, 0))  # white-transparent not black-transparent becauise i think the alpha is premultiplied and we dont want grey


@asynccontextmanager
async def lifespan(_):
	global http
	async with aiohttp.ClientSession() as http:
		yield

app = FastAPI(
	lifespan=lifespan,
	docs_url="/docs" if config.mode == FediiverseMode.DEV else None,
	redoc_url="/redoc" if config.mode == FediiverseMode.DEV else None
)


def http_date(dt: datetime.datetime):
	# https://stackoverflow.com/a/225106
	weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month - 1]
	return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
		weekday, dt.day, month, dt.year, dt.hour, dt.minute, dt.second
	)


class ProxiedImageFormat(Enum):
	JPEG = "jpeg"
	PNG = "png"


class ProxiedImageTarget(BaseModel):
	src: HttpUrl
	max_height: Optional[int] = None
	max_width: Optional[int] = None
	accept: Optional[Literal["jpeg"]] = None
	format: Optional[ProxiedImageFormat] = None
	mask_pfp: bool = False

	def to_token(self) -> str:
		return fernet.encrypt(self.model_dump_json().encode("utf-8")).decode("ascii")

	@classmethod
	def from_token(cls, token: str):
		return cls.model_validate_json(fernet.decrypt(token))


@app.middleware("http")
async def http_middleware(request: Request, call_next):
	response = await call_next(request)
	del response.headers["Server"]
	return response


@app.get("/", response_class=PlainTextResponse)
async def get_root():
	return "hello from fediiverse img :3"


def process_image_data(
	target: ProxiedImageTarget,
	content_type: str,
	source_buffer: io.BytesIO
):
	image = Image.open(
		fp=source_buffer,
		formats=[
			"jpeg" if content_type == "image/jpeg" else
			"png" if content_type == "image/png" else
			"gif" if content_type == "image/gif" else  # yes this will flatten animated GIFs to 1 frame, fixme :(
			"webp"
		]
	)

	original_width, original_height = image.size
	width, height = image.size
	width, height = float(width), float(height)
	max_width, max_height = target.max_width, target.max_height

	if max_width and width > max_width:
		ratio = max_width / width
		width *= ratio
		height *= ratio

	if max_height and height > max_height:
		ratio = max_height / height
		width *= ratio
		height *= ratio

	width = round(width)
	height = round(height)
	if width != original_width or height != original_height:
		image = image.resize(
			size=(width, height),
			resample=Image.Resampling.LANCZOS
		)
	else:
		pass

	if target.mask_pfp:
		if image.mode != "RGBA":
			image = image.convert("RGBA")
		image = Image.composite(blank_image_32, image, pfp_mask_32)

	new_format: ProxiedImageFormat = (
		target.format if target.format else (
			ProxiedImageFormat.PNG if (content_type == "image/png" or image.has_transparency_data) else
			ProxiedImageFormat.JPEG
		)
	)

	out_buffer = io.BytesIO()
	image.save(fp=out_buffer, format=(
		"png" if new_format == ProxiedImageFormat.PNG else
		"jpeg" if new_format == ProxiedImageFormat.JPEG else
		None  # unreachable
	))
	new_content_type = (
		"image/png" if new_format == ProxiedImageFormat.PNG else
		"image/jpeg" if new_format == ProxiedImageFormat.JPEG else
		None
	)

	return out_buffer.getvalue(), new_content_type


@app.get("/img")
async def cache_proxy(t: str):
	target = ProxiedImageTarget.from_token(t)

	src_url = str(target.src)

	async with http.request(
		method="GET",
		url=src_url,
		headers={
			"Accept": (
				"image/jpeg" if target.accept == "jpeg" else "image/jpeg, image/png, image/gif, image/bmp"
			)
		}
	) as response:
		try:
			response.raise_for_status()
		except ClientResponseError:
			raise HTTPException(
				status_code=response.status,
				detail=f"got error {response.status} from parent server"
			)

		if response.content_length > MAX_CONTENT_LENGTH:
			raise HTTPException(
				status_code=500,
				detail="source image is too large"
			)

		content_type = response.headers["Content-Type"]
		etag = response.headers.get("ETag")
		age = response.headers.get("Age")
		last_modified = response.headers["Last-Modified"]
		source_buffer = io.BytesIO(await response.content.read())

	# noinspection PyTypeChecker
	processed_data, processed_content_type = await asyncio.get_event_loop().run_in_executor(
		None,
		lambda: process_image_data(
			target=target,
			content_type=content_type,
			source_buffer=source_buffer
		)
	)

	delta = datetime.timedelta(days=30)
	headers = {
		# these are my desperate efforts to get the 3ds to actually cache images properly
		# but it doesnt want to
		"Content-Type": processed_content_type,
		"ETag": etag,
		"Age": age,
		"Last-Modified": last_modified,
		"Cache-Control": f"max-age={delta.total_seconds()}",  # 30 days
		"Expires": http_date(datetime.datetime.now(datetime.timezone.utc) + delta)
	}
	for key, value in list(headers.items()):
		if value is None:
			del headers[key]

	return Response(
		status_code=200,
		media_type=processed_content_type,
		content=processed_data,
		headers=headers
	)


def get_proxied_url_image(target: ProxiedImageTarget):
	img_server_url = URL.build(
		scheme="https",
		host=hosts.img_host
	) / "img" % {"t": target.to_token()}
	return img_server_url


def get_proxied_url(
	url: str | HttpUrl,
	accept: str = None,
	max_width: Optional[int] = None,
	max_height: Optional[int] = None,
	mask_pfp: bool = False
):
	# str(url) because sometimes i pass a HttpUrl in here
	target = ProxiedImageTarget(
		src=url,
		accept=accept,
		max_width=max_width,
		max_height=max_height,
		mask_pfp=mask_pfp
	)
	result_url = get_proxied_url_image(target)
	return str(result_url)
