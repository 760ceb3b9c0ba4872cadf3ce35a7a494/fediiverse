import base64
import datetime
import io
import os
import json
import re
import string
from pathlib import Path
from typing import Optional, Literal, Annotated, Any

import cairosvg
import aiofiles
import aiohttp
import emoji
from aiohttp import ClientResponseError
from bs4 import BeautifulSoup, Tag
from fastapi import FastAPI, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse, HTMLResponse, Response, RedirectResponse
from fastapi.requests import Request
from yarl import URL
from dotenv import load_dotenv

from .mastodon import Client
from .mastodon.models.custom_emoji import CustomEmoji
from .mastodon.models.filter import FilterAction
from .mastodon.models.media_attachment import MediaAttachmentType
from .mastodon.models.status import Status, StatusVisibility

load_dotenv()

mastodon = Client(
	token=os.getenv("MASTODON_TOKEN"),
	host="https://" + os.getenv("MASTODON_HOST")
)
http = aiohttp.ClientSession()

root_path = Path(__file__).parent
templates_path = root_path / "templates"
static_path = root_path / "static"


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


app = FastAPI()
app.mount(
	path="/static",
	app=NoCacheStaticFiles(
		directory=static_path
	),
	name="static"
)


def http_date(dt: datetime.datetime):
	# https://stackoverflow.com/a/225106
	weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
	month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][dt.month - 1]
	return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
		weekday, dt.day, month, dt.year, dt.hour, dt.minute, dt.second
	)


def proxy_url(url: str, accept: str = None):
	a = URL("/_cache-proxy/") / URL(url).path.removeprefix("/")
	if accept:
		a %= {"accept": accept}
	return str(a)


emoji_path = Path(os.getenv("TWEMOJI_ASSETS_PATH")).expanduser()


def get_emoji_img_src(emoji: str, size: int = 72):
	# remove variant selectors
	if "\u200D" not in emoji:
		emoji = emoji.replace("\uFE0F", "")

	codepoint_str = "-".join(f"{ord(char):x}" for char in emoji)
	svg_path = emoji_path / f"{codepoint_str}.svg"

	with open(svg_path, "rb") as file:
		svg_contents = file.read()

	png_data = cairosvg.svg2png(
		output_width=size,
		output_height=size,
		bytestring=svg_contents
	)

	return "data:image/png;base64," + base64.b64encode(png_data).decode("ascii")


@app.get("/_cache-proxy/{src_path:path}")
async def cache_proxy(
		src_path: str,
		accept: Optional[Literal["jpeg"]] = None,
		*,
		request: Request
):
	src_url = URL("https://" + os.getenv("MASTODON_MEDIA_HOST")) / src_path  # yes this is kinda bad. sowwy ;3

	response = await http.request(
		method="GET",
		url=src_url,
		headers={
			"Accept": (
				"image/jpeg" if accept == "jpeg" else "image/jpeg, image/png, image/gif, image/bmp"
			)
		}
	)

	try:
		response.raise_for_status()
	except ClientResponseError:
		return Response(
			status_code=response.status,
			media_type="text/plain",
			content=f"got error {response.status} from parent server"
		)

	content_type = response.headers["Content-Type"]
	etag = response.headers["ETag"]
	age = response.headers["Age"]
	last_modified = response.headers["Last-Modified"]
	data = await response.content.read()

	delta = datetime.timedelta(days=30)
	headers = {
		# these are my desperate efforts to get the 3ds to actually cache images properly
		# but it doesnt want to
		"Content-Type": content_type,
		"ETag": etag,
		"Age": age,
		"Last-Modified": last_modified,
		"Cache-Control": f"max-age={delta.total_seconds()}",  # 30 days
		"Expires": http_date(datetime.datetime.utcnow() + delta)
	}

	return Response(
		status_code=200,
		media_type=content_type,
		content=data,
		headers=headers
	)


def format_timedelta_short(delta: datetime.timedelta):
	# stolen from humanize
	use_months = True

	years = delta.days // 365
	days = delta.days % 365
	num_months = int(days // 30.5)

	if not years and days < 1:
		if delta.seconds < 10:
			return "now"

		if delta.seconds < 60:
			return f"{delta.seconds}s"

		if 60 <= delta.seconds < 3600:
			minutes = delta.seconds // 60
			return f"{minutes}m"

		if 3600 < delta.seconds:
			hours = delta.seconds // 3600
			return f"{hours}h"
	elif years == 0:
		if not use_months:
			return f"{days}d"

		if not num_months:
			return f"{days}d"

		return f"{num_months}m"

	elif years == 1:
		if not num_months:
			return f"1y {days}d"

		if use_months:
			if num_months == 1:
				return f"1y 1m"

			return f"1y {num_months}m"

		return f"1y {days}d"

	return f"{years}y"


def inline_emojify(text: string, shortcode_index: dict[str, CustomEmoji], soup: BeautifulSoup):
	text_matches: list[dict] = []

	# PHASE 0: parse out the custom emojis
	index = 0
	shortcode_pattern = re.compile(":([a-zA-Z0-9_]+):")

	while True:
		match = shortcode_pattern.search(text, index)
		if not match:
			break

		match_start, match_end = match.span()
		index = match_end

		match_shortcode = match.group(1)
		if match_shortcode not in shortcode_index:
			# invalid emoji
			continue

		text_matches.append({
			"type": "custom_emoji",
			"start": match_start,
			"end": match_end,
			"shortcode": match_shortcode
		})

	# PHASE 1: parse out the unicode emojis
	for emoji_match in emoji.emoji_list(text):
		text_matches.append({
			"type": "emoji",
			"start": emoji_match["match_start"],
			"end": emoji_match["match_end"],
			"emoji": emoji_match["emoji"]
		})

	text_matches.sort(key=lambda match: match["start"])

	# PHASE 2: actually convert the text into usual
	children = []
	index = 0
	for match in text_matches:
		match_type = match["type"]
		match_start = match["start"]
		match_end = match["end"]

		children.append(text[index:match_start])

		if match_type == "custom_emoji":
			match_shortcode = match["shortcode"]

			custom_emoji = shortcode_index[match_shortcode]
			emoji_el = soup.new_tag("img")
			emoji_el["class"] = "custom-emoji"
			emoji_el["src"] = proxy_url(custom_emoji.url)
			children.append(emoji_el)
		elif match_type == "emoji":
			match_emoji = match["emoji"]
			emoji_el = soup.new_tag("img")
			emoji_el["class"] = "emoji"
			emoji_el["src"] = get_emoji_img_src(
				emoji=match_emoji,
				size=16
			)
			children.append(emoji_el)
		else:
			raise NotImplementedError("idfk")

		index = match_end

	children.append(text[index:])  # if theres any left.

	return children


def beautifully_insert_content(
	content: str,
	destination_el: Tag,
	emojis: list[CustomEmoji],
	soup: BeautifulSoup
):
	content_shortcode_index = {
		custom_emoji.shortcode: custom_emoji for custom_emoji in emojis
	}
	content_soup = BeautifulSoup(content, "html.parser")

	def transplant(src_el: Tag, dest_el: Tag):
		for child in list(src_el.children):
			if isinstance(child, Tag):
				tag_name = child.name.lower()
				if tag_name not in {
					"del", "pre", "blockquote", "code", "b",
					"strong", "u", "i", "em", "ul", "ol", "li",
					"h1", "h2", "h3", "h4", "h5", "h6", "p",
					"a", "span", "br"
				}:
					continue

				if tag_name == "a":
					href = child.attrs.get("href")
					attrs = {
						"href": href,
						"target": "_blank",
						"rel": "nofollow noopener noreferrer",  # not like it matters...
						"onclick": f"event.preventDefault(); promptLink({href!r});"
					}
				else:
					attrs = {}

				new_child = soup.new_tag(
					name=tag_name,
					attrs=attrs
				)
				transplant(child, new_child)
				dest_el.append(new_child)
			elif isinstance(child, str):
				text = child
				children = inline_emojify(
					text=text,
					soup=soup,
					shortcode_index=content_shortcode_index
				)
				dest_el.extend(children)
			else:
				continue

	transplant(content_soup, destination_el)


def render_status(status: Status, container: Tag, soup: BeautifulSoup):
	parent_status = status
	status = parent_status.reblog if parent_status.reblog else parent_status

	is_filtered = status.filtered and len(status.filtered)

	status_el = soup.new_tag("div")
	status_el["id"] = f"status-{parent_status.id}"
	status_el["class"] = "status"
	status_el["data-status-id"] = parent_status.id
	status_el["data-status-acct"] = parent_status.account.acct
	status_el["data-visible-status-id"] = status.id
	status_el["data-visible-status-acct"] = status.account.acct

	if is_filtered:
		for filter_result in status.filtered:
			if filter_result.filter.filter_action == FilterAction.HIDE:
				return

		status_el["style"] = "display: none"

		filter_el = soup.new_tag("div", attrs={
			"class": "filter",
			"id": f"status-{parent_status.id}-filter",
			"data-status-id": parent_status.id,
			"data-visible-status-id": status.id
		})

		filter_names = [filter_result.filter.title for filter_result in status.filtered]

		filter_label_el = soup.new_tag("span", attrs={
			"class": "filter__label"
		})
		filter_label_el.string = f"Filtered: " + (", ".join(filter_names))
		filter_el.append(filter_label_el)

		show_button = soup.new_tag("button", attrs={
			"class": "filter__show-button",
			"onclick": "filterShowClicked(this, event)"
		})
		show_button.string = "Show anyway"
		filter_el.append(show_button)

		container.append(filter_el)

	if parent_status != status:
		# if this is a boost post
		prepend_el = soup.new_tag("div")
		prepend_el["class"] = "status__prepend"

		prepend_icon_container_el = soup.new_tag("div")
		prepend_icon_container_el["class"] = "status__prepend-icon-container"

		prepend_icon_el = soup.new_tag("img")
		prepend_icon_el["class"] = "status__prepend-icon"
		prepend_icon_el["src"] = "/static/icons/reblog.png"
		prepend_icon_container_el.append(prepend_icon_el)

		prepend_el.append(prepend_icon_container_el)

		prepend_label_el = soup.new_tag("span")
		prepend_label_el["class"] = "status__prepend-label"

		prepend_user_el = soup.new_tag("span")
		prepend_user_el["class"] = "status__prepend-user"
		prepend_user_el.extend(inline_emojify(
			text=parent_status.account.display_name,
			soup=soup,
			shortcode_index={
				custom_emoji.shortcode: custom_emoji for custom_emoji in parent_status.account.emojis
			}
		))
		prepend_label_el.append(prepend_user_el)

		prepend_label_el.append(" boosted")

		prepend_el.append(prepend_label_el)

		status_el.append(prepend_el)

	header_el = soup.new_tag("a")
	header_el["href"] = f"/profile/{status.account.id}"
	header_el["class"] = "status__header"

	proxied_av_url = proxy_url(status.account.avatar)
	pfp_el = soup.new_tag("img")
	pfp_el["class"] = "status__avatar"
	pfp_el["src"] = str(proxied_av_url)
	header_el.append(pfp_el)

	names_el = soup.new_tag("div")
	names_el["class"] = "status__names"

	display_name_el = soup.new_tag("span")
	display_name_el["class"] = "status__display-name"
	display_name_el.extend(inline_emojify(
		text=status.account.display_name,
		soup=soup,
		shortcode_index={
			custom_emoji.shortcode: custom_emoji for custom_emoji in status.account.emojis
		}
	))
	names_el.append(display_name_el)

	acct_name_el = soup.new_tag("span")
	acct_name_el["class"] = "status__acct-name"
	acct_name_el.string = "@" + status.account.acct
	names_el.append(acct_name_el)

	header_el.append(names_el)

	status_el.append(header_el)

	# RENDER SPOILER
	if status.spoiler_text:
		spoiler_el = soup.new_tag("div", attrs={"class": "status__spoiler"})
		spoiler_text_el = soup.new_tag("span", attrs={"class": "status__spoiler-text"})
		spoiler_text_el.string = status.spoiler_text
		spoiler_el.append(spoiler_text_el)

		spoiler_button_el = soup.new_tag("button", attrs={
			"class": "status__spoiler-button",
			"onclick": "spoilerClicked(this, event)"
		})
		spoiler_button_el.string = "Show"
		spoiler_el.append(spoiler_button_el)
		status_el.append(spoiler_el)

	# RENDER CONTENT:
	content_el = soup.new_tag("div", attrs={
		"class": "status__content",
		"style": "display: none" if status.spoiler_text else ""
	})

	# RENDER CONTENT TEXT:
	content_text_el = soup.new_tag("div")
	content_text_el["class"] = "status__content-text rendered-text"
	beautifully_insert_content(
		content=status.content,
		destination_el=content_text_el,
		emojis=status.emojis,
		soup=soup
	)
	content_el.append(content_text_el)

	# RENDER CONTENT MEDIA:
	if status.media_attachments and len(status.media_attachments):
		media_gallery = soup.new_tag("table", attrs={"class": "media-gallery"})

		attachments = [attachment for attachment in status.media_attachments if
					   attachment.type == MediaAttachmentType.IMAGE]
		for row_index in range(0, len(attachments), 2):
			row_attachments = attachments[row_index:row_index + 2]
			row_el = soup.new_tag("tr", attrs={"class": "media-gallery__row"})
			for attachment in row_attachments:
				alone_in_row = len(row_attachments) == 1
				attachment_el = soup.new_tag("td", attrs={
					"class": "media-gallery__item",
					"colspan": "2" if alone_in_row else "1"
				})

				aspect_ratio = attachment.meta["small"]["aspect"]
				min_height = 72
				ideal_height = (306 if alone_in_row else 151) * (1 / aspect_ratio)
				max_height = 230

				actual_min_height = max(min_height, min(ideal_height, max_height))
				image_el = soup.new_tag("div", attrs={
					"class": "media-gallery__item-img",
					"style": "; ".join([
						f"background-image: url({proxy_url(attachment.preview_url)!r})",
						f"min-height: {actual_min_height}px",
						f"max-height: {max_height}px"
					]),
					"role": "img",
					"title": attachment.description,
					"alt": attachment.description
				})

				image_button_el = soup.new_tag("button", attrs={
					"class": "media-gallery__item-button",
					"onclick": f"previewImage({proxy_url(attachment.url, accept='jpeg')!r}, {parent_status.id!r})",
					# "onkeydown": f"if (event.keyCode == 13) previewImage({proxy_url(attachment.url, accept='jpeg')!r}, {parent_status.id!r})",
				})
				image_el.append(image_button_el)

				if attachment.description:
					alt_el = soup.new_tag("button", attrs={
						"class": "media-gallery__item-alt-button",
						"onclick": "altClicked(this, event)"
					})
					alt_el.string = "Alt"
					image_el.append(alt_el)

				attachment_el.append(image_el)
				row_el.append(attachment_el)

			media_gallery.append(row_el)

		content_el.append(media_gallery)

	status_el.append(content_el)

	actions_el = soup.new_tag("div", attrs={"class": "status__actions"})

	def make_action(
			*,
			# label: str,
			active: bool = False,
			disabled: bool = False,

			icon: str,
			active_icon: Optional[str],
			callback: str  # (this, event) => void
	):
		attrs = {
			"class": "status__action",
			"data-icon": icon,
			"data-active-icon": active_icon if active_icon else icon,
			"onClick": f"{callback}(this, event)"
		}
		if disabled:
			attrs["disabled"] = "true"
		if active:
			attrs["data-active"] = "true"
		action_el = soup.new_tag(
			name="button",
			attrs=attrs
		)
		action_inner_el = soup.new_tag("div", attrs={"class": "status__action-inner"})
		action_inner_el.append(
			soup.new_tag("img", attrs={"src": f"/static/icons/{active_icon if active else icon}.png"}))
		# action_inner_el.append(label)
		action_el.append(action_inner_el)
		actions_el.append(action_el)

	timedelta_el = soup.new_tag("span", attrs={
		"class": "status__timedelta"
	})
	timedelta_el.string = format_timedelta_short(datetime.datetime.now(datetime.timezone.utc) - status.created_at)
	actions_el.append(timedelta_el)

	actions_el.append(soup.new_tag("div", attrs={
		"style": "display: block; -webkit-box-flex: 1;"
	}))

	if is_filtered:
		make_action(
			icon="eye",
			active_icon="eye-active",
			active=False,
			callback="hideClicked(this, event)"
		)

	make_action(
		# label="Bookmarked" if status.bookmarked else "Bookmark",
		icon="reply",
		active_icon="reply-active",
		active=False,
		callback="replyClicked"
	)
	make_action(
		# label="Boosted" if status.reblogged else "Boost",
		icon="reblog",
		active_icon="reblog-active",
		active=status.reblogged,
		disabled=status.visibility not in {
			StatusVisibility.PUBLIC,
			StatusVisibility.UNLISTED
		},
		callback="reblogClicked"
	)
	make_action(
		# label="Favorited" if status.favourited else "Favorite",
		icon="favourite",
		active_icon="favourite-active",
		active=status.favourited,
		callback="favouriteClicked"
	)
	make_action(
		# label="Bookmarked" if status.bookmarked else "Bookmark",
		icon="bookmark",
		active_icon="bookmark-active",
		active=status.bookmarked,
		callback="bookmarkClicked"
	)

	status_el.append(actions_el)
	container.append(status_el)

	return status_el


@app.get("/mediaPreview", response_class=HTMLResponse)
async def media_preview(url: str):
	async with aiofiles.open(templates_path / "mediaPreview.html", "r") as file:
		html = await file.read()

	soup = BeautifulSoup(html, "html.parser")
	soup.find(name="img")["src"] = url
	return HTMLResponse(
		content=str(soup)
	)


@app.get("/titles/show", response_class=RedirectResponse)
async def titles_show_route():
	return RedirectResponse(
		url="/timeline?kind=home"
	)


@app.post("/status/{status_id}/reblog")
async def reblog_status(
		status_id: str,
		visibility: Optional[Literal["public", "unlisted", "private"]] = None
):
	await mastodon.statuses.reblog(
		status_id=status_id,
		visibility=visibility
	)


@app.post("/status/{status_id}/unreblog")
async def unreblog_status(status_id: str):
	await mastodon.statuses.unreblog(status_id)


@app.post("/status/{status_id}/favourite")
async def favourite_status(status_id: str):
	await mastodon.statuses.favourite(status_id)


@app.post("/status/{status_id}/unfavourite")
async def unfavourite_status(status_id: str):
	await mastodon.statuses.unfavourite(status_id)


@app.post("/status/{status_id}/bookmark")
async def bookmark_status(status_id: str):
	await mastodon.statuses.bookmark(status_id)


@app.post("/status/{status_id}/unbookmark")
async def unbookmark_status(status_id: str):
	await mastodon.statuses.unbookmark(status_id)


@app.on_event("startup")
async def on_startup():
	await mastodon.__aenter__()
	await http.__aenter__()


@app.on_event("shutdown")
async def on_shutdown():
	await mastodon.__aexit__(None, None, None)
	await http.__aexit__(None, None, None)


@app.get("/profile/{account_id}", response_class=HTMLResponse)
async def profile(
		account_id: str
):
	async with aiofiles.open(templates_path / "profile.html", "r") as file:
		html = await file.read()
	soup = BeautifulSoup(html, "html.parser")
	account = await mastodon.accounts.get_account(account_id)

	profile_banner_el = soup.select_one(".profile__banner")
	profile_banner_el["style"] = f"background-image: url({proxy_url(account.header, accept='jpeg')!r})"

	profile_avatar_el = soup.select_one(".profile__avatar")
	profile_avatar_el["src"] = proxy_url(account.avatar, accept="jpeg")

	display_name_el = soup.select_one(".profile__display-name")
	display_name_el.extend(inline_emojify(
		text=account.display_name,
		soup=soup,
		shortcode_index={
			custom_emoji.shortcode: custom_emoji for custom_emoji in account.emojis
		}
	))

	acct_name_el = soup.select_one(".profile__acct-name")
	acct_name_el.string = f"@{account.acct}"

	description_el = soup.select_one(".profile-description")
	description_text_el = soup.select_one(".profile-description__text")
	if account.note:
		beautifully_insert_content(
			content=account.note,
			destination_el=description_text_el,
			emojis=account.emojis,
			soup=soup
		)
	else:
		description_el.decompose()

	stats_el = soup.select_one(".profile__stats")

	def add_stat(label: str, value: int):
		stat_el = soup.new_tag("span", attrs={"class": "profile-stat"})
		stat_value_el = soup.new_tag("span", attrs={"class": "profile-stat__value"})
		stat_value_el.string = f"{value:,}"
		stat_el.append(stat_value_el)
		stat_el.append(" ")
		stat_el.append(label)
		stats_el.append(stat_el)

	add_stat("posts", account.statuses_count)
	add_stat("following", account.following_count)
	add_stat("followers", account.followers_count)

	fields_el = soup.select_one(".profile-fields")
	if account.fields and len(account.fields):
		for field in account.fields:
			field_el = soup.new_tag("div", attrs={"class": "profile-field"})
			if field.verified_at:
				field_el["data-verified"] = "true"

			field_name_el = soup.new_tag("span", attrs={"class": "profile-field__name"})
			beautifully_insert_content(
				content=field.name,
				destination_el=field_name_el,
				emojis=account.emojis,
				soup=soup
			)
			field_el.append(field_name_el)

			field_value_el = soup.new_tag("span", attrs={"class": "profile-field__value"})
			beautifully_insert_content(
				content=field.value,
				destination_el=field_value_el,
				emojis=account.emojis,
				soup=soup
			)
			field_el.append(field_value_el)

			fields_el.append(field_el)
	else:
		fields_el.decompose()

	limit = 40

	timeline = await mastodon.accounts.get_account_statuses(
		account_id=account_id,
		limit=limit
	)

	list_el = soup.select_one(".status-list")
	for status in timeline:
		# print(post)
		status_el = render_status(status, list_el, soup)

	return HTMLResponse(
		content=str(soup)
	)


@app.get("/timeline", response_class=HTMLResponse)
async def main(
		kind: Literal["home", "trending", "local", "federated"],
		max_id: Optional[str] = None,
		offset: Optional[int] = None,

		user_agent: Annotated[str | None, Header()] = None
):
	# https://en-americas-support.nintendo.com/app/answers/detail/a_id/13802/~/nintendo-3ds-internet-browser-specs
	is_3ds = user_agent and "Nintendo 3DS" in user_agent
	is_netfront_nx = user_agent and " NX/" in user_agent
	is_miiverse = is_3ds and is_netfront_nx and user_agent and " miiverse/" in user_agent

	async with aiofiles.open(templates_path / "timeline.html", "r") as file:
		html = await file.read()
	soup = BeautifulSoup(html, "html.parser")

	# used for applying some additional css hacks for miiverse browser specifically
	soup.find("html")["data-is-miiverse"] = "true" if is_miiverse else "false"

	limit = 40
	if kind == "home":
		tab_id = "tab-home"
		timeline = await mastodon.timelines.get_home_timeline(
			limit=limit,
			max_id=max_id
		)
	elif kind == "trending":
		tab_id = "tab-explore"
		timeline = await mastodon.trends.get_trending_statuses(
			limit=limit,
			offset=offset
		)
	elif kind == "local":
		tab_id = "tab-local"
		timeline = await mastodon.timelines.get_public_timeline(
			limit=limit,
			max_id=max_id,
			local=True
		)
	elif kind == "federated":
		tab_id = "tab-federated"
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

	active_tab = soup.find(attrs={"id": tab_id})
	active_tab["src"] = active_tab["src"].replace("-up", "-down")

	new_max_id = timeline[len(timeline) - 1].id
	# instance = await mastodon.instance.get_instance()

	header_banner_el = soup.select_one(".header__banner")
	header_banner_el["style"] = f"background-image: url(/static/placeholder.jpg)"

	if kind == "trending":
		load_older_url = f"/timeline?kind={kind}&offset={(offset or 0) + limit}"
	else:
		load_older_url = f"/timeline?kind={kind}&max_id={new_max_id}"

	load_older_el = soup.select_one("#load-older-button")
	if potentially_has_more:
		load_older_el["onClick"] = f'document.location = {load_older_url!r}'
	else:
		load_older_el.decompose()  # DECOMPOSE???

	list_el = soup.select_one(".status-list")

	for status in timeline:
		render_status(status, list_el, soup)

	return HTMLResponse(
		content=str(soup)
	)
