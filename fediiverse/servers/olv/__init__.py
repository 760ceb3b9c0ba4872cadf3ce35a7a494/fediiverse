import base64
import datetime
import io
import json
import warnings
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Literal, Annotated, Any

import aiohttp.client_exceptions
import cryptography.fernet
from PIL import Image
from aiohttp import ClientResponseError
from bs4 import BeautifulSoup
from fastapi import FastAPI, Header, Form, Depends, Query, HTTPException, UploadFile, File
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, Response, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from .rendering import render_header_user
from ...mastodon import Client
from ...mastodon.models.account import Account
from ...mastodon.models.status import StatusVisibility
from ...servers.olv.rendering import render_status, render_profile, run_as_async, load_template
from ...storage import FediiverseStore, get_config, FediiverseMode
from ...token import FediiverseToken
from ...version import FEDIIVERSE_VERSION_STR

config = get_config()
hosts = config.hosts

root_path = Path(__file__).parent
templates_path = root_path / "templates"
static_path = root_path / "static"


class ContextAwareRedirectResponse(HTMLResponse):
	def __init__(self, url: str):
		# HACK HACK HACK HACK HACK HACK !!!!!!!!!!!
		encoded_url = json.dumps(url)

		encoded_url += ' + "'
		if "?" in encoded_url:
			encoded_url += "&"
		else:
			encoded_url += "?"
		encoded_url += "token="
		encoded_url += '"'
		encoded_url += ' + '
		encoded_url += 'token'

		super().__init__(
			content="""<!DOCTYPE html>
<html>
<head>
<script>
var token = cave.lls_getItem("token");
var firstTimeComplete = cave.lls_getItem("first-time-complete") == "true";

if (token) {
	if (firstTimeComplete) {
		document.location = <LOC>;
	} else {
		document.location = "/first-time?token=" + token;
	}
} else {
	document.location = "/logged-out";
}
</script>
</head>
</html>""".replace("<LOC>", encoded_url)
		)


class CaveErrorResponse(HTMLResponse):
	def __init__(self, error_message: str, status_code: int = 500):
		super().__init__(
			content=f"""
<!DOCTYPE html>
<html>
<head>
<script>
cave.transition_end();
cave.snd_playSe("SE_CTR_COMMON_ERROR");
cave.error_callFreeErrorViewer(0, {json.dumps(error_message)});
history.back();
</script>
</head>
</html>""",
			status_code=status_code
		)


class NoCacheStaticFiles(StaticFiles):
	# https://stackoverflow.com/a/77823873
	def __init__(self, *args: Any, **kwargs: Any):
		self.cache_control = "max-age=0, no-cache, no-store, must-revalidate"
		self.pragma = "no-cache"
		self.expires = "0"
		super().__init__(*args, **kwargs)

	def is_not_modified(
			self, *args: Any, **kwargs: Any
	) -> bool:
		return False

	def file_response(self, *args: Any, **kwargs: Any) -> Response:
		resp = super().file_response(*args, **kwargs)
		resp.headers.setdefault("Cache-Control", self.cache_control)
		resp.headers.setdefault("Pragma", self.pragma)
		resp.headers.setdefault("Expires", self.expires)
		return resp


if config.mode == FediiverseMode.DEV:
	warnings.warn("!! Running in dev mode - caching disabled")
	static_class = NoCacheStaticFiles
else:
	static_class = StaticFiles


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
app.mount(
	path="/static",
	app=static_class(
		directory=static_path
	),
	name="static"
)


async def token_dep(
		token_q: Annotated[Optional[str], Query(alias="token")] = None,
		token_h: Annotated[Optional[str], Header(alias="Token")] = None,
):
	token = token_q or token_h
	if not token:
		raise HTTPException(status_code=401, detail="No authentication token was specified with the request.")
	fediiverse_token = FediiverseToken.from_encrypted(token)
	yield fediiverse_token


async def mastodon_dep(fediiverse_token: Annotated[FediiverseToken, Depends(token_dep)]):
	async with Client(
		host=f"https://{fediiverse_token.domain}",
		token=fediiverse_token.access_token
	) as mastodon:
		yield mastodon


class ParamPack(BaseModel):
	title_id: int
	access_key: int
	platform_id: int
	region_id: int
	language_id: int
	country_id: int
	area_id: int
	network_restriction: int
	friend_restriction: int
	rating_restriction: int
	rating_organization: int
	transferable_id: int
	tz_name: str
	utc_offset: int  # in seconds
	remaster_version: int


async def parampack_dep(
		parampack_header: Annotated[Optional[str], Header(alias="X-Nintendo-ParamPack", max_length=512)] = None
) -> ParamPack | None:
	if parampack_header is None:
		return None

	data = base64.b64decode(parampack_header.replace(" ", "")).decode("ascii")
	# delimiter is a backslash \  , idk if it can be escaped so im assuming no
	parts = data.strip("\\").split("\\")

	parampack_dict = {}
	for index in range(0, len(parts), 2):
		name = parts[index]
		value = parts[index+1]
		parampack_dict[name] = value

	return ParamPack.model_validate(parampack_dict)


async def utc_offset_dep(
		parampack: Annotated[Optional[ParamPack], Depends(parampack_dep)] = None
) -> datetime.timedelta | None:
	if parampack:
		return datetime.timedelta(seconds=parampack.utc_offset)

	return None


async def user_id_dep(fediiverse_token: Annotated[FediiverseToken, Depends(token_dep)]):
	yield fediiverse_token.user_id


async def acct_dep(fediiverse_token: Annotated[FediiverseToken, Depends(token_dep)]):
	yield fediiverse_token.acct


async def is_miiverse_dep(user_agent: Annotated[str | None, Header()]):
	yield is_user_agent_miiverse(user_agent)


class TemplateDep:
	def __init__(self, filename: str):
		self.filename = filename

	async def __call__(
		self,
		is_miiverse: Annotated[bool, Depends(is_miiverse_dep)],
		user_id: Annotated[str, Depends(user_id_dep)]
	):
		yield await load_template(self.filename, user_id=user_id, is_miiverse=is_miiverse)


class UnauthedTemplateDep:
	def __init__(self, filename: str):
		self.filename = filename

	async def __call__(
		self,
		is_miiverse: Annotated[bool, Depends(is_miiverse_dep)]
	):
		yield await load_template(self.filename, user_id="", is_miiverse=is_miiverse)


@app.get("/", response_class=PlainTextResponse)
async def get_root():
	return "hello from fediiverse olv :3"


@app.get("/status/{status_id}", response_class=HTMLResponse)
async def status_route(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	user_id: Annotated[str, Depends(user_id_dep)],
	soup: Annotated[BeautifulSoup, Depends(TemplateDep("status.html"))],
	status_id: str,
	utc_offset: Annotated[Optional[datetime.timedelta], Depends(utc_offset_dep)] = None,
	page: int = 0,
):
	status = await mastodon.statuses.get(status_id)
	context = await mastodon.statuses.get_context(status_id)

	ancestor_limit = 8
	descendant_limit = 20
	descendant_offset = page * descendant_limit

	has_more_ancestors = len(context.ancestors) > ancestor_limit
	has_more_descendants = (len(context.descendants) - descendant_offset) > descendant_limit

	load_more_ancestors_button = soup.select_one("#load-more-ancestors-button")
	if has_more_ancestors:
		# viewing earlier ancestors in the thread just opens the status page of an earlier ancestor
		new_focus_ancestor = context.ancestors[-ancestor_limit]
		load_more_ancestors_button["href"] = f"/status/{new_focus_ancestor.id}"
	else:
		load_more_ancestors_button.decompose()

	load_more_descendants_button = soup.select_one("#load-more-descendants-button")
	if has_more_descendants:
		# viewing later descendants in the thread changes which of the descendants of this status specifically are shown
		load_more_descendants_button["href"] = f"/status/{status.id}?page={page+1}"
	else:
		load_more_descendants_button.decompose()

	list_el = soup.select_one(".status-list")

	for ancestor_status in context.ancestors[-ancestor_limit:]:
		await run_as_async(lambda: render_status(
			ancestor_status, list_el, soup,
			local_user_id=user_id,
			expanded=False,
			utc_offset=utc_offset
		))

	main_status_el = await run_as_async(lambda: render_status(
		status, list_el, soup,
		local_user_id=user_id,
		expanded=True,
		utc_offset=utc_offset
	))
	main_status_el.attrs["class"] += " main-status"

	if page > 0:
		older_indicator_el = soup.new_tag("span", attrs={"class": "older-post-indicator"})
		older_indicator_el.string = f"Page {page+1}"
		list_el.append(older_indicator_el)

	for descendant_status in context.descendants[descendant_offset:descendant_offset+descendant_limit]:
		await run_as_async(lambda: render_status(
			descendant_status, list_el, soup,
			local_user_id=user_id,
			expanded=False,
			utc_offset=utc_offset
		))

	return HTMLResponse(content=str(soup))


@app.get("/logged-out", response_class=HTMLResponse)
async def logged_out_route(
	soup: Annotated[BeautifulSoup, Depends(UnauthedTemplateDep("logged-out.html"))],
):
	return HTMLResponse(content=str(soup))


@app.get("/first-time", response_class=HTMLResponse)
async def first_time_route(
	fediiverse_token: Annotated[FediiverseToken, Depends(token_dep)],
	soup: Annotated[BeautifulSoup, Depends(UnauthedTemplateDep("first-time.html"))],
):
	soup.select_one("#user-name").string = f"@{fediiverse_token.acct}"
	soup.select_one("#inst-name").string = hosts.welcome_host
	soup.select_one("#inst-version").string = f"{FEDIIVERSE_VERSION_STR} beta"

	return HTMLResponse(content=str(soup))


@app.get("/settings", response_class=HTMLResponse)
async def settings_route(
	soup: Annotated[BeautifulSoup, Depends(TemplateDep("settings.html"))],
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	fediiverse_token: Annotated[FediiverseToken, Depends(token_dep)],
	utc_offset: Annotated[Optional[datetime.timedelta], Depends(utc_offset_dep)] = None
):
	account = await mastodon.accounts.get_local_account()
	timezone = datetime.timezone(utc_offset) if utc_offset is not None else datetime.timezone.utc

	soup.select_one("#settings-fields__version").string = f"fediiverse v{FEDIIVERSE_VERSION_STR} beta"
	soup.select_one("#settings-fields__instances").string = f"{mastodon.host_url.host} via {hosts.welcome_host}"
	soup.select_one("#settings-fields__session").string = f"Logged in {fediiverse_token.timestamp.astimezone(timezone).strftime('%b %e, %Y at %k:%M %Z')}"

	if config.mode != FediiverseMode.DEV:
		soup.select_one("#settings-fields__dev").decompose()

	soup.select_one(".user-row").append(render_header_user(account=account, soup=soup, link=False))

	return HTMLResponse(content=str(soup))


@app.get("/new", response_class=HTMLResponse)
async def new_route(
	soup: Annotated[BeautifulSoup, Depends(TemplateDep("new.html"))],
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	user_id: Annotated[str, Depends(user_id_dep)],
	our_acct: Annotated[str, Depends(acct_dep)],
	reply_to: Optional[str] = None,
	default_content: str = ""
):
	header_el = soup.find(class_="new-header")

	reply_to_status = (await mastodon.statuses.get(reply_to)) if reply_to else None

	# handle the default visibility of this post
	preferences = await mastodon.preferences.get_preferences()
	user_preferred_visibility = StatusVisibility(preferences["posting:default:visibility"])
	visibility_order = list(StatusVisibility)  # from least->most strict

	# the default visibility of the new post should be:
	# the account default visibility OR the reply-to post visibility, whichever is STRICTER.

	if reply_to:
		reply_to_visibility = reply_to_status.visibility

		visibility = visibility_order[max([
			visibility_order.index(user_preferred_visibility),
			visibility_order.index(reply_to_visibility)
		])]

		# https://stackoverflow.com/a/53657523
		mentioned_accts: list[str] = list(dict.fromkeys([
			*(mention.acct for mention in reply_to_status.mentions),
			reply_to_status.account.acct
		]))
		mentioned_accts = [acct for acct in mentioned_accts if acct != our_acct]  # we dont need to tag yourself!

		if len(mentioned_accts) and default_content == "":
			default_content = (" ".join([f"@{acct}" for acct in mentioned_accts])) + " "
	else:
		visibility = user_preferred_visibility

	soup.find("textarea").string = default_content

	visibility_el = soup.find(attrs={"id": "visibility"})
	# noinspection PyTypeChecker
	visibility_el["value"] = visibility.value

	reply_to_field_el = soup.find(attrs={"id": "reply_to"})
	reply_to_field_el["value"] = reply_to

	# render the entire thread
	thread_elements = []
	thread_status = reply_to_status
	while thread_status and len(thread_elements) <= 10:  # well, 10 replies in the thread at most.
		# add the preview of the status being replied to
		thread_status_el = soup.new_tag("div", attrs={"class": "reply-to"})
		await run_as_async(lambda: render_status(
			status=thread_status,
			container=thread_status_el,
			soup=soup,
			local_user_id=user_id,
			include_actions=False,
			disable_selection=True
		))
		thread_elements.append(thread_status_el)
		if thread_status.in_reply_to_id:
			thread_status = await mastodon.statuses.get(thread_status.in_reply_to_id)
		else:
			thread_status = None

	for thread_status_el in reversed(thread_elements):
		header_el.append(thread_status_el)

	return HTMLResponse(content=str(soup))


def process_sketch_to_png(sketch_bmp_b64: str) -> io.BytesIO:
	sketch_bmp = base64.b64decode(sketch_bmp_b64)
	sketch_bmp_io = io.BytesIO(sketch_bmp)
	sketch_bmp_io.seek(0)
	sketch_png_io = io.BytesIO()
	with Image.open(sketch_bmp_io) as sketch_img:
		sketch_img.save(sketch_png_io, "png")
	sketch_png_io.seek(0)
	return sketch_png_io


def stitch_screenshot(
	capture_bottom: bytes,
	capture_top: bytes,
	# capture_top_left_eye: bytes,
	# capture_top_right_eye: bytes
) -> io.BytesIO:
	bottom_img = Image.open(io.BytesIO(capture_bottom), formats=["jpeg"])
	if bottom_img.size != (320, 240):
		raise ValueError("invalid size")

	top_img = Image.open(io.BytesIO(capture_top), formats=["jpeg"])
	if top_img.size != (400, 240):
		raise ValueError("invalid size")

	# ignoring top_right_img for now

	final_image = Image.new("RGBA", size=(400, 480))
	final_image.paste(top_img, (0, 0, 400, 240))
	final_image.paste(bottom_img, (40, 240, 40+320, 240+240))

	out = io.BytesIO()
	final_image.save(out, "png")
	out.seek(0)
	return out


def reencode_jpeg_as_png(jpeg_bytes: bytes):
	image = Image.open(io.BytesIO(jpeg_bytes), formats=["jpeg"])
	out = io.BytesIO()
	image.save(out, "png")
	out.seek(0)
	return out


@app.post("/new", response_class=RedirectResponse)
async def post_new(
	*,
	content: Annotated[Optional[str], Form()] = None,
	visibility: Annotated[StatusVisibility, Form()],
	sketch_bmp_b64: Annotated[Optional[str], Form(alias="sketch", max_length=0x2000)] = None,
	reply_to: Annotated[Optional[str], Form()] = None,
	content_warning: Annotated[Optional[str], Form()] = None,

	capture_bottom: Annotated[Optional[UploadFile], File()] = None,
	capture_top: Annotated[Optional[UploadFile], File()] = None,
	# capture_top_left_eye: Annotated[Optional[UploadFile], File()] = None,
	# capture_top_right_eye: Annotated[Optional[UploadFile], File()] = None,

	mastodon: Annotated[Client, Depends(mastodon_dep)]
):
	has_top_screenshot = capture_top and capture_top.size
	has_bottom_screenshot = capture_bottom and capture_bottom.size
	has_screenshot = has_top_screenshot or has_bottom_screenshot
	has_content = (
		sketch_bmp_b64 or content or has_screenshot
	)
	if not has_content:
		raise HTTPException(status_code=400, detail="No content provided")

	if has_screenshot:
		capture_bottom_jpeg_bytes = await capture_bottom.read() if has_bottom_screenshot else None
		capture_top_jpeg_bytes = await capture_top.read() if has_top_screenshot else None

		# if we have both top and bottom, stitch them as one PNG
		if has_bottom_screenshot and has_top_screenshot:
			screenshot_file_bytes = await run_as_async(lambda: stitch_screenshot(
				capture_bottom=capture_bottom_jpeg_bytes,
				capture_top=capture_top_jpeg_bytes
			))
			screenshot_file_name = "fediiverse-screenshot.png"
			screenshot_file_content_type = "image/png"
		else:
			# JPEG images get crushed by the server so i'm going to reencode them as PNG
			screenshot_file_bytes = reencode_jpeg_as_png(capture_top_jpeg_bytes or capture_bottom_jpeg_bytes)
			screenshot_file_name = "fediiverse-screenshot.png"
			screenshot_file_content_type = "image/png"
	else:
		screenshot_file_bytes = None
		screenshot_file_name = None
		screenshot_file_content_type = None

	media_ids = []
	if screenshot_file_bytes:
		attachment_upload = await mastodon.media.upload(
			file=screenshot_file_bytes,
			file_name=screenshot_file_name,
			file_content_type=screenshot_file_content_type
		)
		media_ids.append(attachment_upload.id)

	if sketch_bmp_b64:
		sketch_png_io = await run_as_async(lambda: process_sketch_to_png(sketch_bmp_b64))

		attachment_upload = await mastodon.media.upload(
			file=sketch_png_io,
			file_name="sketch_3ds.png",
			file_content_type="image/png"
		)
		media_ids.append(attachment_upload.id)

	_status = await mastodon.statuses.post(
		status=content,
		media_ids=media_ids,
		visibility=visibility,
		in_reply_to_id=reply_to,
		spoiler_text=content_warning
	)

	return ContextAwareRedirectResponse(
		url="/timeline?kind=home"
	)


@app.get("/media-preview", response_class=HTMLResponse)
async def media_preview(
	soup: Annotated[BeautifulSoup, Depends(TemplateDep("mediaPreview.html"))],
	url: str
):
	soup.find(name="img")["src"] = url
	return HTMLResponse(content=str(soup))


@app.get("/test", response_class=HTMLResponse)
async def test(
	soup: Annotated[BeautifulSoup, Depends(TemplateDep("test.html"))],
):
	return HTMLResponse(content=str(soup))


# noinspection PyUnusedLocal
@app.get("/communities/{community_id}", response_class=HTMLResponse)
async def communities_0(
	community_id: int,
):
	return ContextAwareRedirectResponse(
		url="/timeline?kind=home"
	)


@app.get("/titles/show", response_class=ContextAwareRedirectResponse)
async def titles_show_route():
	return ContextAwareRedirectResponse(
		url="/timeline?kind=home"
	)


@app.get("/status/{status_id}/reblog")
@app.post("/status/{status_id}/reblog")
async def reblog_status(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	status_id: str,
	visibility: Optional[Literal["public", "unlisted", "private"]] = None
):
	await mastodon.statuses.reblog(
		status_id=status_id,
		visibility=visibility
	)


@app.get("/status/{status_id}/delete")
@app.post("/status/{status_id}/delete")
async def delete_status(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	status_id: str
):
	await mastodon.statuses.delete(status_id)


@app.get("/status/{status_id}/unreblog")
@app.post("/status/{status_id}/unreblog")
async def unreblog_status(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	status_id: str
):
	await mastodon.statuses.unreblog(status_id)


@app.get("/status/{status_id}/favourite")
@app.post("/status/{status_id}/favourite")
async def favourite_status(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	status_id: str
):
	await mastodon.statuses.favourite(status_id)


@app.get("/status/{status_id}/unfavourite")
@app.post("/status/{status_id}/unfavourite")
async def unfavourite_status(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	status_id: str
):
	await mastodon.statuses.unfavourite(status_id)


@app.get("/status/{status_id}/bookmark")
@app.post("/status/{status_id}/bookmark")
async def bookmark_status(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	status_id: str
):
	await mastodon.statuses.bookmark(status_id)


@app.get("/status/{status_id}/unbookmark")
@app.post("/status/{status_id}/unbookmark")
async def unbookmark_status(
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	status_id: str
):
	await mastodon.statuses.unbookmark(status_id)


@app.get("/logout")
@app.post("/logout")
async def logout(
	fediiverse_token: Annotated[FediiverseToken, Depends(token_dep)]
):
	saved_instance = await store.get_saved_instance(fediiverse_token.domain)
	if saved_instance is None:
		raise HTTPException(status_code=400, detail="Instance not found")

	# we can use an unauthorized client for this
	async with Client(host=f"https://{fediiverse_token.domain}") as mastodon:
		await mastodon.oauth.revoke_access_token(
			client_id=saved_instance.client_id,
			client_secret=saved_instance.client_secret,
			token=fediiverse_token.access_token
		)


async def render_profile_page(
	account: Account,
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	user_id: Annotated[str, Depends(user_id_dep)],
	is_miiverse: Annotated[bool, Depends(is_miiverse_dep)],
	max_id: Optional[str] = None,
	utc_offset: Optional[datetime.timedelta] = None
) -> BeautifulSoup:
	soup, new_max_id = await render_profile(
		account,
		mastodon=mastodon,
		user_id=user_id,
		max_id=max_id,
		include_description=not max_id,
		include_fields=not max_id,
		utc_offset=utc_offset,
		is_miiverse=is_miiverse
	)
	soup.find("html")["data-local-user-id"] = user_id

	potentially_has_more = not not new_max_id
	load_older_el = soup.select_one("#load-older-button")
	if potentially_has_more:
		load_older_url = f"/profile/{account.id}?max_id={new_max_id}"
		load_older_el.attrs["href"] = load_older_url
	else:
		load_older_el.decompose()  # DECOMPOSE???

	return soup


@app.get("/profile/{account_id}", response_class=HTMLResponse)
async def profile_route(
	account_id: str,
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	user_id: Annotated[str, Depends(user_id_dep)],
	is_miiverse: Annotated[bool, Depends(is_miiverse_dep)],
	max_id: Optional[str] = None,
	utc_offset: Annotated[Optional[datetime.timedelta], Depends(utc_offset_dep)] = None
):
	account = await mastodon.accounts.get_account(account_id)

	return HTMLResponse(content=str(await render_profile_page(
		account=account,
		mastodon=mastodon,
		user_id=user_id,
		max_id=max_id,
		utc_offset=utc_offset,
		is_miiverse=is_miiverse
	)))


@app.get("/acct/{acct}", response_class=HTMLResponse)
async def acct_route(
	acct: str,
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	user_id: Annotated[str, Depends(user_id_dep)],
	is_miiverse: Annotated[bool, Depends(is_miiverse_dep)],
	utc_offset: Annotated[Optional[datetime.timedelta], Depends(utc_offset_dep)] = None
):
	try:
		account = await mastodon.accounts.lookup_account(acct)
	except ClientResponseError as error:
		if error.status == 404:
			raise HTTPException(status_code=404, detail=f"User @{acct} was not found.")
		else:
			raise error from None

	return HTMLResponse(content=str(await render_profile_page(
		account=account,
		mastodon=mastodon,
		user_id=user_id,
		utc_offset=utc_offset,
		is_miiverse=is_miiverse,
		# no max_id needed
	)))


def is_user_agent_miiverse(user_agent: str) -> bool:
	# https://en-americas-support.nintendo.com/app/answers/detail/a_id/13802/~/nintendo-3ds-internet-browser-specs
	is_3ds = user_agent and "Nintendo 3DS" in user_agent
	is_netfront_nx = user_agent and " NX/" in user_agent  # it's really WebKit but it's lying!
	is_miiverse = is_3ds and is_netfront_nx and user_agent and " miiverse/" in user_agent
	return is_miiverse


# noinspection PyUnusedLocal
@app.get("/timeline", response_class=HTMLResponse)
async def timeline_route(
	*,
	kind: Literal["home", "trending", "local", "federated"],
	max_id: Optional[str] = None,
	offset: Optional[int] = None,

	user_agent: Annotated[str | None, Header()] = None,
	mastodon: Annotated[Client, Depends(mastodon_dep)],
	user_id: Annotated[str, Depends(user_id_dep)],
	soup: Annotated[BeautifulSoup, Depends(TemplateDep("timeline.html"))]
):
	is_miiverse = is_user_agent_miiverse(user_agent)

	viewing_older_el = soup.select_one("#viewing-older")
	if not (offset or max_id):
		viewing_older_el.decompose()

	limit = 20
	if kind == "home":
		heading = "Home timeline"
		timeline = await mastodon.timelines.get_home_timeline(
			limit=limit,
			max_id=max_id
		)
	elif kind == "trending":
		heading = "Trending timeline"
		timeline = await mastodon.trends.get_trending_statuses(
			limit=limit,
			offset=offset
		)
	elif kind == "local":
		heading = "Local timeline"
		timeline = await mastodon.timelines.get_public_timeline(
			limit=limit,
			max_id=max_id,
			local=True
		)
	elif kind == "federated":
		heading = "Federated timeline"
		timeline = await mastodon.timelines.get_public_timeline(
			limit=limit,
			max_id=max_id,
			# local AND remote, all of it!
		)
	else:
		raise Exception

	potentially_has_more = len(timeline) >= limit

	html_el = soup.find("html")
	html_el["data-timeline-kind"] = kind

	new_max_id = timeline[len(timeline) - 1].id
	# instance = await mastodon.instance.get_instance()

	heading_el = soup.select_one(".header h1")
	heading_el.string = heading

	if kind == "trending":
		load_older_url = f"/timeline?kind={kind}&offset={(offset or 0) + limit}"
	else:
		load_older_url = f"/timeline?kind={kind}&max_id={new_max_id}"

	load_older_el = soup.select_one("#load-older-button")
	load_older_el.attrs["href"] = load_older_url
	if not potentially_has_more:
		load_older_el.decompose()  # DECOMPOSE???

	list_el = soup.select_one(".status-list")

	for status in timeline:
		await run_as_async(lambda: render_status(status, list_el, soup, local_user_id=user_id))

	return HTMLResponse(
		content=str(soup)
	)


# noinspection PyUnusedLocal
@app.exception_handler(500)
async def exception_handler(request, exception) -> CaveErrorResponse | PlainTextResponse:
	is_miiverse = is_user_agent_miiverse(request.headers.get("User-Agent"))
	if is_miiverse:
		return CaveErrorResponse(
			error_message="An internal server error occurred. If you encounter a bug, please file an issue on the fediiverse GitHub, thx!!!",
			status_code=500
		)
	else:
		return PlainTextResponse(
			content="Internal server error nooooo TwT",
			status_code=500
		)


LOGOUT_HTML = """<!DOCTYPE html>
<html>
<head>
<script>
cave.lls_removeItem("token");
document.location = "/logged-out";
</script>
</head>
</html>"""


@app.exception_handler(cryptography.fernet.InvalidToken)
async def aiohttp_exception_handler(
		request: Request,
		exception: cryptography.fernet.InvalidToken
) -> HTMLResponse:
	is_miiverse = is_user_agent_miiverse(request.headers.get("User-Agent"))
	if is_miiverse:
		return HTMLResponse(content=LOGOUT_HTML)
	else:
		raise exception


@app.exception_handler(aiohttp.client_exceptions.ClientResponseError)
async def aiohttp_exception_handler(
		request: Request,
		exception: aiohttp.client_exceptions.ClientResponseError
) -> HTMLResponse:
	is_miiverse = is_user_agent_miiverse(request.headers.get("User-Agent"))
	if is_miiverse and exception.status == 401:
		return HTMLResponse(content=LOGOUT_HTML)
	else:
		raise exception


@app.exception_handler(StarletteHTTPException)
async def exception_handler(
		request: Request,
		exception: StarletteHTTPException
) -> CaveErrorResponse | PlainTextResponse:
	is_miiverse = is_user_agent_miiverse(request.headers.get("User-Agent"))
	if is_miiverse:
		return CaveErrorResponse(
			error_message=f"Error {exception.status_code}: {exception.detail}\n\nIf you encounter a bug, please file an issue on the fediiverse GitHub, thx!!!",
			status_code=exception.status_code
		)
	else:
		return PlainTextResponse(
			content=exception.detail,
			status_code=exception.status_code
		)
