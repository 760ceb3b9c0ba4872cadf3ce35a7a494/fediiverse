import base64
import datetime
import io
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Optional

import aiohttp
import qrcode
import validators
from PIL import Image
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel
from yarl import URL

from ...instance_check import is_allowed_instance_domain_name
from ...mastodon import Client
from ...mastodon.providers.oauth import GrantType
from ...storage import FediiverseStore, SavedInstance, get_config, FediiverseMode
from ...token import FediiverseToken
from ...version import FEDIIVERSE_VERSION_STR

root_path = Path(__file__).parent
static_path = root_path / "static"
templates_path = root_path / "templates"

config = get_config()
hosts = config.hosts
fernet: Fernet = Fernet(config.secrets.temporal_secret_key)
store = FediiverseStore()


@asynccontextmanager
async def lifespan(_):
	async with store:
		yield


app = FastAPI(
	lifespan=lifespan,
	docs_url="/docs" if config.mode == FediiverseMode.DEV else None,
	redoc_url="/redoc" if config.mode == FediiverseMode.DEV else None
)
app.mount("/static", StaticFiles(directory=static_path), name="static")


WEBSITE_URL = URL.build(scheme="https", host=hosts.welcome_host)
RETURN_URL = WEBSITE_URL / "return"


class OAuthState(BaseModel):
	# state held temporarily during the oauth process
	domain: str

	def to_token(self) -> str:
		return fernet.encrypt(self.model_dump_json().encode("utf-8")).decode("ascii")

	@classmethod
	def from_token(cls, token: str):
		return cls.model_validate_json(fernet.decrypt(token))


async def validate_instance_domain(host: str) -> bool:
	# 1. check if its even a valid domain name
	if not validators.domain(host):
		return False

	# 2. check if its an instance
	try:
		async with Client(f"https://{host}") as mastodon:
			instance = await mastodon.instance.get_instance_v1()
			if instance.uri != host:
				return False
	except aiohttp.ClientError as exception:
		traceback.print_exception(exception)
		return False

	return True


async def build_instance_app_at_domain(domain: str) -> SavedInstance:
	timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
	async with Client(f"https://{domain}") as mastodon:
		application = await mastodon.apps.create_application(
			client_name="fediiverse for Nintendo 3DS",
			redirect_uris=[str(RETURN_URL)],
			scopes=["read", "write", "follow"],
			website=str(WEBSITE_URL)
		)

	return SavedInstance(
		domain_name=domain,
		client_id=application.client_id,
		client_secret=application.client_secret,
		created_at=timestamp
	)


@app.post("/select-instance")
async def select_instance(
	*,
	domain_name: Annotated[str, Form(
		pattern=r"^[a-zA-Z0-9\.\-]*$"
	)],
):
	domain_name = domain_name.lower()  # case insensitive

	domain_name_allowed = await is_allowed_instance_domain_name(domain_name)
	if not domain_name_allowed:
		raise HTTPException(
			status_code=400,
			detail=f"Instance {domain_name!r} is not supported."
		)

	host_valid = await validate_instance_domain(domain_name)
	if not host_valid:
		raise HTTPException(
			status_code=400,
			detail=f"Failed to reach the instance at {domain_name!r}."
		)

	instance_info = await store.get_saved_instance(domain_name)
	if not instance_info:
		# we haven't seen this instance before!
		instance_info = await build_instance_app_at_domain(domain_name)
		await store.save_instance(instance_info)

	state = OAuthState(
		domain=domain_name
	)

	authorize_url = URL.build(
		scheme="https",
		host=domain_name
	) / "oauth" / "authorize" % {
		"client_id": instance_info.client_id,
		"response_type": "code",
		"scope": "read write",
		"force_login": "true",
		"redirect_uri": str(RETURN_URL),
		"state": state.to_token()
	}
	return RedirectResponse(
		url=str(authorize_url),
		status_code=303
	)


with open(templates_path / "index.html", "r") as file:
	index_template_html = file.read()


@app.get("/", response_class=HTMLResponse)
async def get_root():
	soup = BeautifulSoup(index_template_html, "html.parser")

	soup.select_one("#host").string = hosts.welcome_host
	soup.select_one("#version").string = FEDIIVERSE_VERSION_STR

	intro_el = soup.select_one("#intro-html")
	if config.welcome.additional_intro_html:
		inner_soup = BeautifulSoup(config.welcome.additional_intro_html, "html.parser")
		intro_el.clear()
		intro_el.append(inner_soup)
	else:
		intro_el.decompose()

	if config.instances.allowlist and config.instances.allowlist_dropdown:
		soup.select_one("input#domain-name").decompose()
		for domain_name in config.instances.allowlist:
			tag = soup.new_tag("option", attrs={
				"value": domain_name
			})
			tag.string = domain_name
			soup.select_one("select#domain-name").append(tag)
	else:
		soup.select_one("select#domain-name").decompose()
		soup.select_one("input#domain-name").attrs["placeholder"] = config.instances.instance_placeholder

	return HTMLResponse(
		content=str(soup)
	)


with open(templates_path / "return.html", "r") as file:
	return_template_html = file.read()


def render_return(
	acct: str,
	qr_value: str
):
	soup = BeautifulSoup(return_template_html, "html.parser")

	qrcode_img: Image.Image = qrcode.make(qr_value, box_size=1)
	real_box_size = 3

	qr_png_buffer = io.BytesIO()
	qrcode_img.save(qr_png_buffer, "png")

	qr_png_b64 = base64.b64encode(qr_png_buffer.getvalue()).decode("ascii")
	qr_data_url = f"data:image/png;base64,{qr_png_b64}"

	style_size = qrcode_img.height * real_box_size

	soup.select_one("#acct").string = f"@{acct}"
	soup.select_one("#qr").attrs.update({
		"src": qr_data_url,
		"width": style_size,
		"height": style_size
	})

	return str(soup)


# noinspection PyUnusedLocal
@app.get("/return")
async def return_route(
	*,
	error: Optional[str] = None,
	error_description: Optional[str] = None,
	code: Optional[str] = None,
	state: str
):
	state = OAuthState.from_token(state)

	if error is not None:
		raise HTTPException(
			status_code=400,
			detail="Authorization request denied. Please try again!"
		)

	if code is None:
		raise HTTPException(
			status_code=400,
			detail="Authorization code is missing."
		)

	instance_info = await store.get_saved_instance(state.domain)
	if not instance_info:
		raise ValueError(f"no instance info for {state.domain}")

	async with Client(host=f"https://{state.domain}") as mastodon:
		try:
			token_response = await mastodon.oauth.obtain_access_token(
				grant_type=GrantType.AUTHORIZATION_CODE,
				code=code,
				client_id=instance_info.client_id,
				client_secret=instance_info.client_secret,
				redirect_uri=str(RETURN_URL),
				scope=["read", "write"]
			)
		except aiohttp.ClientResponseError as exception:
			if exception.status == 400:
				return RedirectResponse(
					status_code=307,
					url="/"
				)
			else:
				raise HTTPException(
					status_code=500,
					detail="Invalid OAuth credentials or other OAuth error"
				)

		mastodon.set_token(token_response.access_token)
		user = await mastodon.accounts.get_local_account()

		fediiverse_token = FediiverseToken(
			user_id=user.id,
			domain=state.domain,
			acct=user.acct,
			access_token=token_response.access_token,
			timestamp=datetime.datetime.now(datetime.timezone.utc)
		)

		qrcode_value = ";".join([
			"fediiverse",
			f"http://{hosts.setup_host}",
			f"https://{hosts.discovery_host}/v",
			fediiverse_token.to_encrypted()
		])

		return HTMLResponse(
			content=render_return(
				acct=user.acct,
				qr_value=qrcode_value
			)
		)


with open(templates_path / "error.html", "r") as file:
	error_template_html = file.read()


# noinspection PyUnusedLocal
@app.exception_handler(StarletteHTTPException)
async def exception_handler(
		request: Request,
		exception: StarletteHTTPException
) -> HTMLResponse:
	soup = BeautifulSoup(error_template_html, "html.parser")
	soup.select_one("#error").string = f"Error {exception.status_code}"
	soup.select_one("#error-description").string = f"{exception.detail}"

	return HTMLResponse(
		status_code=exception.status_code,
		content=str(soup)
	)
