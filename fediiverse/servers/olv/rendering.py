import asyncio
import base64
import datetime
import re
import string
import warnings
from pathlib import Path
from typing import Optional, Callable

import aiofiles
import cairosvg
import emoji as emoji_lib
from bs4 import BeautifulSoup, Tag
from yarl import URL

from ...mastodon import Client
from ...mastodon.models.account import Account
from ...mastodon.models.custom_emoji import CustomEmoji
from ...mastodon.models.filter import FilterAction
from ...mastodon.models.media_attachment import MediaAttachmentType, MediaAttachment
from ...mastodon.models.preview_card import PreviewCardType
from ...mastodon.models.status import Status, StatusVisibility
from ...servers.img import get_proxied_url
from ...storage import get_config, FediiverseMode, EMOJIS_PATH
from ...version import FEDIIVERSE_VERSION_STR

config = get_config()
root_path = Path(__file__).parent
templates_path = root_path / "templates"
static_path = root_path / "static"


async def run_as_async(func: Callable):
	# noinspection PyTypeChecker
	return await asyncio.get_event_loop().run_in_executor(None, func)


def get_emoji_img_src(emoji: str, size: int = 72) -> Optional[str]:
	# remove variant selectors
	if "\u200D" not in emoji:
		emoji = emoji.replace("\uFE0F", "")

	codepoint_str = "-".join(f"{ord(char):x}" for char in emoji)
	svg_path = EMOJIS_PATH / f"{codepoint_str}.svg"
	if not svg_path.exists():
		return None

	# this is blocking but we use run_as_async higher up
	with open(svg_path, "rb") as file:
		svg_contents = file.read()

	png_data = cairosvg.svg2png(
		output_width=size,
		output_height=size,
		bytestring=svg_contents
	)

	return "data:image/png;base64," + base64.b64encode(png_data).decode("ascii")


def inline_emojify(
		text: string,
		soup: BeautifulSoup,
		*,
		shortcode_index: Optional[dict[str, CustomEmoji]] = None,
):
	"""
	returns a list of elements representing the input string with all emojis converted to inline emoji elements.
	if shortcode_index is specified custom emojis are also converted.
	"""

	text_matches: list[dict] = []

	if shortcode_index:
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
	for emoji_match in emoji_lib.emoji_list(text):
		text_matches.append({
			"type": "emoji",
			"start": emoji_match["match_start"],
			"end": emoji_match["match_end"],
			"emoji": emoji_match["emoji"]
		})

	text_matches.sort(key=lambda match_: match_["start"])

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
			emoji_el["src"] = get_proxied_url(custom_emoji.url, max_height=32)  # resizes down to both 16px and 14px
			children.append(emoji_el)
		elif match_type == "emoji":
			match_emoji = match["emoji"]
			emoji_src = get_emoji_img_src(
				emoji=match_emoji,
				size=16
			)

			if emoji_src:
				emoji_el = soup.new_tag("img")
				emoji_el["class"] = "emoji"
				emoji_el["src"] = emoji_src
				children.append(emoji_el)
			else:
				warnings.warn(f"warning: couldn't find emoji {match_emoji!r}")
		else:
			raise NotImplementedError("idfk")

		index = match_end

	children.append(text[index:])  # if theres any left.

	return children


acct_mention_regex = re.compile("^@([a-zA-Z0-9_.-]+)(?:@([a-z0-9_.-]+))?$")  # matches: @a@a or @a


def check_if_acct_mention(
		text: str,
		href: str
) -> Optional[str]:
	"""
	check if a link with content `text` and href `href` is a link to another account
	"""
	acct_mention_match = acct_mention_regex.match(text)
	if not acct_mention_match:
		return None

	mentioned_username: str = acct_mention_match.group(1)
	mentioned_host: str | None = acct_mention_match.group(2)  # not always present

	href_url = URL(href)
	url_host = href_url.host

	if mentioned_host and url_host != mentioned_host:
		return None

	if len(href_url.parts) == 3:
		if not href_url.parts[1] in {"users", "u"}:
			return None
		url_username = href_url.parts[2]
	elif len(href_url.parts) == 2:
		if not href_url.parts[1].startswith("@"):
			return None
		url_username = href_url.parts[1].removeprefix("@")
	else:
		return None

	if mentioned_username != url_username:
		return None

	return f"{url_username}@{url_host}"


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

					# special case for user mentions
					acct = check_if_acct_mention(child.text, href)

					if acct:
						attrs = {
							"href": f"/acct/{acct}",
							"contextual": ""
						}
					else:
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


def render_header_user(account: Account, soup: BeautifulSoup, link: bool = True):
	if link:
		header_el = soup.new_tag("a")
		header_el["href"] = f"/profile/{account.id}"
		header_el["class"] = "header-user"
		header_el["contextual"] = ""
	else:
		header_el = soup.new_tag("div", attrs={"class": "header-user"})

	proxied_av_url = get_proxied_url(account.avatar, max_width=32, max_height=32, mask_pfp=True)
	pfp_el = soup.new_tag("img")
	pfp_el["class"] = "header-user__avatar"
	pfp_el["src"] = str(proxied_av_url)
	header_el.append(pfp_el)

	names_el = soup.new_tag("div")
	names_el["class"] = "header-user__names"

	display_name_el = soup.new_tag("span")
	display_name_el["class"] = "header-user__display-name"
	display_name_el.extend(inline_emojify(
		text=account.display_name,
		soup=soup,
		shortcode_index={
			custom_emoji.shortcode: custom_emoji for custom_emoji in account.emojis
		}
	))
	names_el.append(display_name_el)

	acct_name_el = soup.new_tag("span")
	acct_name_el["class"] = "header-user__acct-name"
	acct_name_el.string = "@" + account.acct
	names_el.append(acct_name_el)

	header_el.append(names_el)
	return header_el


def render_stat(soup: BeautifulSoup, label: str, value: int):
	stat_el = soup.new_tag("span", attrs={"class": "stat"})
	stat_value_el = soup.new_tag("span", attrs={"class": "stat__value"})
	stat_value_el.string = f"{value:,}"
	stat_el.append(stat_value_el)
	stat_el.append(" ")
	stat_el.append(label)
	return stat_el


def render_status(
		status: Status,
		container: Tag,
		soup: BeautifulSoup,
		*,
		local_user_id: str,
		include_actions: bool = True,
		disable_selection: bool = False,
		expanded: bool = False,
		utc_offset: Optional[datetime.timedelta] = None
) -> Tag | None:
	parent_status = status
	status = parent_status.reblog if parent_status.reblog else parent_status

	is_filtered = status.filtered and len(status.filtered)

	status_el = soup.new_tag("div")
	status_el["id"] = f"status-{parent_status.id}"
	status_el["class"] = "status"
	status_el["data-status-id"] = parent_status.id
	status_el["data-status-acct"] = parent_status.account.acct
	status_el["data-status-by-me"] = "true" if parent_status.account.id == local_user_id else "false"
	status_el["data-visible-status-id"] = status.id
	status_el["data-visible-status-acct"] = status.account.acct
	status_el["data-visible-status-by-me"] = "true" if status.account.id == local_user_id else "false"
	status_el["data-expanded"] = "true" if expanded else "false"

	if is_filtered:
		for filter_result in status.filtered:
			if filter_result.filter.filter_action == FilterAction.HIDE:
				return None

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

		filter_label_el.append(soup.new_string("Filtered: "))
		inner_tag = soup.new_tag("span", attrs={"class": "filter__name"})
		inner_tag.string = ", ".join(filter_names)
		filter_label_el.append(inner_tag)

		filter_el.append(filter_label_el)

		show_button = soup.new_tag("button", attrs={
			"class": "button",
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

		prepend_icon_el = soup.new_tag("div")
		prepend_icon_el["class"] = "icon status__prepend-icon"
		prepend_icon_el["icon"] = "reblog"
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

	header_el = render_header_user(status.account, soup)
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

	# if theres 1 attachment thats 320x120 in size (3ds sketches) make it full width and dont table it

	sketch_attachment: Optional[MediaAttachment] = None
	attachments = []
	for attachment in status.media_attachments:
		if (
				attachment.meta
				and "original" in attachment.meta
				and attachment.meta["original"].get("width") == 320
				and attachment.meta["original"].get("height") == 120
		) and not sketch_attachment:
			sketch_attachment = attachment
		else:
			attachments.append(attachment)

	if sketch_attachment:
		sketch_el = soup.new_tag("img", attrs={
			"class": "status__sketch",
			"src": get_proxied_url(sketch_attachment.url)
		})
		content_el.append(sketch_el)

	if attachments and len(attachments):
		media_gallery = soup.new_tag("table", attrs={"class": "media-gallery"})

		attachments = [
			attachment for attachment in attachments if
			attachment.type == MediaAttachmentType.IMAGE
		]
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

				preview_img_url = get_proxied_url(attachment.preview_url, max_width=306, max_height=max_height)
				full_size_img_url = get_proxied_url(attachment.url, max_width=400, max_height=1024)

				actual_min_height = max(min_height, min(ideal_height, max_height))
				image_el = soup.new_tag("div", attrs={
					"class": "media-gallery__item-img",
					"style": "; ".join([
						f"background-image: url({preview_img_url!r})",
						f"min-height: {actual_min_height}px",
						f"max-height: {max_height}px"
					]),
					"role": "img",
					"title": attachment.description,
					"alt": attachment.description
				})

				image_button_el = soup.new_tag("button", attrs={
					"class": "media-gallery__item-button",
					"onclick": f"previewImage({str(full_size_img_url)!r}, {parent_status.id!r})",
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

	# RENDER CONTENT CARD:
	if status.card:
		card = status.card

		if card.provider_name:
			provider = card.provider_name
		elif card.url:
			provider = URL(card.url).host
		else:
			provider = None

		interactive = card.type == PreviewCardType.VIDEO
		large_image = interactive or (card.image and (card.width > card.height))

		card_el = soup.new_tag("a", attrs={
			"class": "status-card",
			"data-large-image": "true" if large_image else "false",

			"href": card.url,
			"target": "_blank",
			"rel": "nofollow noopener noreferrer",  # not like it matters...
			"onclick": f"event.preventDefault(); promptLink({card.url!r});"
		})

		if card.image:
			card_image_el = soup.new_tag("div", attrs={
				"class": "status-card__image",
				"style": f"background-image: url({get_proxied_url(card.image, max_width=309, max_height=174)!r})"
			})
			card_el.append(card_image_el)

		card_content_el = soup.new_tag("div", attrs={
			"class": "status-card__content"
		})
		card_host_el = soup.new_tag("span", attrs={
			"class": "status-card__host"
		})
		if provider:
			card_provider_el = soup.new_tag("span")
			card_provider_el.extend(inline_emojify(provider, soup))
			card_host_el.append(card_provider_el)
		card_content_el.append(card_host_el)

		card_title_el = soup.new_tag("span", attrs={
			"class": "status-card__title"
		})
		card_title_el.extend(inline_emojify(card.title, soup))
		card_content_el.append(card_title_el)

		if card.author_name:
			card_author_el = soup.new_tag("span", attrs={
				"class": "status-card__author"
			})
			card_author_el.append("by ")
			card_author_el.extend(inline_emojify(card.author_name, soup))
			card_content_el.append(card_author_el)
		elif card.description:
			card_description_el = soup.new_tag("span", attrs={
				"class": "status-card__description"
			})
			card_description_el.extend(inline_emojify(card.description, soup))
			card_content_el.append(card_description_el)

		card_el.append(card_content_el)

		content_el.append(card_el)

	status_el.append(content_el)

	if expanded:
		# RENDER META:
		meta_el = soup.new_tag("div", attrs={"class": "status__meta"})

		timezone = datetime.timezone(utc_offset) if utc_offset is not None else datetime.timezone.utc
		timestamp_el = soup.new_tag("span")
		timestamp_el.string = status.created_at.astimezone(timezone).strftime("%b %e, %Y at %k:%M")
		meta_el.append(timestamp_el)

		if status.application:
			meta_el.append(" • ")

			application_el = soup.new_tag("span")
			application_el.string = status.application.name
			meta_el.append(application_el)

		# meta_el.append(soup.new_tag("div", attrs={
		# 	"style": "display: block; -webkit-box-flex: 1;"
		# }))

		visibility_el = soup.new_tag("span", attrs={"class": "status__meta-visibility"})
		visibility_el.append(soup.new_tag("div", attrs={
			"class": "icon",
			"icon": (
				"earth" if status.visibility == StatusVisibility.PUBLIC else
				"moon" if status.visibility == StatusVisibility.UNLISTED else
				"lock" if status.visibility == StatusVisibility.PRIVATE else
				"at" if status.visibility == StatusVisibility.DIRECT else
				"err"
			)
		}))
		visibility_el.append(" ")
		visibility_el.append((
			"Public" if status.visibility == StatusVisibility.PUBLIC else
			"Unlisted" if status.visibility == StatusVisibility.UNLISTED else
			"Private" if status.visibility == StatusVisibility.PRIVATE else
			"Direct" if status.visibility == StatusVisibility.DIRECT else
			"UNKNOWN"
		))
		meta_el.append(visibility_el)

		status_el.append(meta_el)

	if expanded:
		# RENDER STATS:
		stats_el = soup.new_tag("div", attrs={"class": "status__stats"})

		def add_stat(label: str, value: int):
			stats_el.append(render_stat(soup, label, value))

		add_stat("boost" if status.reblogs_count == 1 else "boosts", status.reblogs_count)
		add_stat("favorite" if status.favourites_count == 1 else "favorites", status.favourites_count)
		if status.replies_count > 1:
			add_stat("reply" if status.replies_count == 1 else "replies", status.replies_count)
		status_el.append(stats_el)

	# RENDER ACTIONS:
	actions_el = soup.new_tag("div", attrs={"class": "status__actions"})

	def make_action(
			*,
			label: Optional[str] = None,
			active: bool = False,
			disabled: bool = False,

			icon: str,
			callback: str  # (this, event) => void
	):
		attrs = {
			"class": "status__action",
			"onClick": f"{callback}(this, event)"
		}
		if label:
			attrs["data-text"] = "true"
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
			soup.new_tag("div", attrs={"class": "icon", "icon": icon}))
		if label:
			action_inner_el.append(label)
		action_el.append(action_inner_el)
		actions_el.append(action_el)

	if not expanded:
		# time_delta = datetime.datetime.now(datetime.timezone.utc) - status.created_at

		timedelta_el = soup.new_tag("a", attrs={
			"class": "status__timedelta",
			"data-timestamp-type": "timedelta",
			"data-timestamp": int(status.created_at.timestamp()),
			"contextual": "",
			"href": f"/status/{status.id}"
		})
		timedelta_el.string = "---"
		actions_el.append(timedelta_el)

	actions_el.append(soup.new_tag("div", attrs={
		"style": "display: block; -webkit-box-flex: 1;"
	}))

	if include_actions:
		make_action(
			icon="ellipsis",
			active=False,
			callback="moreClicked"
		)

		if is_filtered:
			make_action(
				icon="eye",
				active=False,
				callback="hideClicked"
			)

		make_action(
			# label="Bookmarked" if status.bookmarked else "Bookmark",
			# label=f"{status.replies_count:,}",
			icon="reply",
			active=False,
			callback="replyClicked"
		)
		make_action(
			# label="Boosted" if status.reblogged else "Boost",
			# label=f"{status.reblogs_count:,}",
			icon="reblog",
			active=status.reblogged,
			disabled=status.visibility not in {
				StatusVisibility.PUBLIC,
				StatusVisibility.UNLISTED
			},
			callback="reblogClicked"
		)
		make_action(
			# label=f"{status.favourites_count:,}",
			icon="favourite",
			active=status.favourited,
			callback="favouriteClicked"
		)
		make_action(
			# label="Bookmarked" if status.bookmarked else "Bookmark",
			icon="bookmark",
			active=status.bookmarked,
			callback="bookmarkClicked"
		)

	if disable_selection:
		for el in status_el.find_all("a", recursive=True):
			el["tabindex"] = "-1"

	status_el.append(actions_el)
	container.append(status_el)

	return status_el


_cached_templates: dict[str, str] = {}


async def load_template(filename: str, *, user_id: str, is_miiverse: bool) -> BeautifulSoup:
	html = _cached_templates.get(filename)
	if not html:
		async with aiofiles.open(templates_path / filename, "r") as file:
			html = await file.read()
			if config.mode == FediiverseMode.PROD:
				_cached_templates[filename] = html

	soup = BeautifulSoup(html, "html.parser")

	# used for applying some additional css hacks for miiverse browser specifically
	root_el = soup.find("html")
	root_el["data-is-miiverse"] = "true" if is_miiverse else "false"
	root_el["data-local-user-id"] = user_id
	root_el["data-version"] = FEDIIVERSE_VERSION_STR

	return soup


async def render_profile(
		account: Account,
		*,
		mastodon: Client,
		user_id: str,
		max_id: Optional[str] = None,
		include_description: bool = True,
		include_fields: bool = True,
		utc_offset: Optional[datetime.timedelta] = None,
		is_miiverse: bool = False
) -> tuple[BeautifulSoup, str | None]:
	soup = await load_template("profile.html", user_id=user_id, is_miiverse=is_miiverse)

	older_post_indicator_el = soup.select_one(".older-post-indicator")
	if max_id is not None:
		snowflake = int(max_id, 10)
		snowflake_timestamp = datetime.datetime.fromtimestamp(
			((snowflake >> (8 * 2)) & (pow(2, (8 * 6)) - 1)) / 1000,
			tz=datetime.timezone.utc
		)
		date_string = snowflake_timestamp.strftime("%B %e, %Y")
		older_post_indicator_el.string = f"Viewing posts from before {date_string}"
	else:
		older_post_indicator_el.decompose()

	profile_el = soup.select_one(".profile")
	if account.id == user_id:
		profile_el["data-is-me"] = "true"

	profile_banner_el = soup.select_one(".profile__banner")
	profile_banner_el[
		"style"] = f"background-image: url({get_proxied_url(account.header, max_width=400, max_height=400)!r})"

	profile_avatar_el = soup.select_one(".profile__avatar")
	profile_avatar_el["src"] = get_proxied_url(account.avatar, max_height=52, max_width=52)

	display_name_el = soup.select_one(".profile__display-name")
	# noinspection PyTypeChecker
	display_name_el.extend(await asyncio.get_event_loop().run_in_executor(None, lambda: inline_emojify(
		text=account.display_name,
		soup=soup,
		shortcode_index={
			custom_emoji.shortcode: custom_emoji for custom_emoji in account.emojis
		}
	)))

	acct_name_el = soup.select_one(".profile__acct-name")
	acct_name_el.string = f"@{account.acct}"

	description_el = soup.select_one(".profile-description")
	description_text_el = soup.select_one(".profile-description__text")
	if include_description and account.note:
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
		stats_el.append(render_stat(soup, label, value))

	add_stat("post" if account.statuses_count == 1 else "posts", account.statuses_count)
	add_stat("following", account.following_count)
	if account.followers_count >= 0:
		add_stat("follower" if account.followers_count == 1 else "followers", account.followers_count)

	fields_el = soup.select_one(".profile-fields")
	if include_fields and account.fields and len(account.fields):
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

	limit = 20

	timeline = await mastodon.accounts.get_account_statuses(
		max_id=max_id,
		account_id=account.id,
		limit=limit
	)

	list_el = soup.select_one(".status-list")
	for status in timeline:
		await run_as_async(lambda: render_status(status, list_el, soup, local_user_id=user_id, utc_offset=utc_offset))

	try:
		new_max_id = timeline[len(timeline) - 1].id
	except IndexError:
		new_max_id = None

	return soup, new_max_id
