function bgmFunc() {
    var setBgm = cave.lls_getItem("bgm");
    var lastBgm = cave.ls_getItem("last-bgm");
    if (!setBgm) {
        setBgm = "BGM_CAVE_SETTING";
        cave.lls_setItem("bgm", setBgm);
    };

    cave.snd_playBgm(setBgm);  // Fixes first-launch issue where ls last-bgm is still set from before.
    if (lastBgm != setBgm) {
        cave.ls_setItem("last-bgm", setBgm);
        cave.snd_stopBgm(100);   // first parameter is time to fade out in milliseconds

        if (setBgm != "<none>") {
            // cave.snd_changeScene();
            cave.snd_playBgm(setBgm);
        }
    }
}

function versionFunc() {
    var lastSeenVersion = cave.lls_getItem("last-seen-version");
    var currentVersion = document.documentElement.getAttribute("data-version");
    // TODO: add update logic here!
    cave.lls_setItem("last-seen-version", currentVersion);
}

function init() {
    bgmFunc();
    versionFunc();

    if (window.location.pathname.startsWith("/timeline")) {
        showOneTimeHint("reload", "Hint: At any time, press \uE004 and \uE005 at the same time to reload and get up to date!");
    }

    var returnScrollHeight = cave.ls_getItem("returnScrollHeight");
    if (returnScrollHeight) {
        cave.brw_scrollImmediately(0, parseInt(returnScrollHeight))
        cave.ls_removeItem("returnScrollHeight");
    } else {
        cave.brw_scrollImmediately(0, 0);
    }

	cave.ls_setGuestModeLaunched(true);
    cave.ls_setCanUseCachedServiceToken(true);  // skips logging in on every launch, greatly speeding up the process.
    cave.lls_setItem("agree_olv", "1");
};

function previewImage(src, statusId) {
    cave.transition_begin();
    cave.ls_setItem("returnScrollHeight", cave.brw_getScrollTopY().toString());
    window.location = "/media-preview?url=" + encodeURIComponent(src) + "&token=" + encodeURIComponent(cave.lls_getItem("token"));
}

function promptLink(href) {
    var dialogResult = cave.dialog_twoButton("", href, "\uE001 Cancel", "\uE000 Open");
    if (dialogResult == 1) {
        cave.jump_toWebbrs(href);  // open href in web browser
    }
}

function getActiveState(actionEl) {
    return actionEl.getAttribute("data-active") == "true";
}

function updateActiveState(actionEl, active) {
    var icon = actionEl.getAttribute("data-icon");
    var activeIcon = actionEl.getAttribute("data-active-icon");
    var iconEl = actionEl.getElementsByTagName(".icon")[0];

    if (active) {
        actionEl.setAttribute("data-active", "true");
        iconEl.setAttribute("src", "/static/icons/" + activeIcon + ".png");
    } else {
        actionEl.setAttribute("data-active", "false");
        iconEl.setAttribute("src", "/static/icons/" + icon + ".png");
    }
}

function favouriteClicked(buttonEl, event) {
    var favourited = getActiveState(buttonEl);
    var statusEl = buttonEl.parentElement.parentElement
    var statusId = statusEl.getAttribute("data-visible-status-id");

    cave.snd_playSe("SE_OLV_OK");
    gfetch("/status/" + statusId + (favourited ? "/unfavourite" : "/favourite"), { method: "POST" }).then(function (response) {
        if (!favourited) {
            cave.snd_playSe("SE_OLV_MII_ADD");
        }
        updateActiveState(buttonEl, !favourited);
    })
}

function bookmarkClicked(buttonEl, event) {
    var bookmarked = getActiveState(buttonEl);
    var statusEl = buttonEl.parentElement.parentElement
    var statusId = statusEl.getAttribute("data-visible-status-id");

    cave.snd_playSe("SE_OLV_OK");
    gfetch("/status/" + statusId + (bookmarked ? "/unbookmark" : "/bookmark"), { method: "POST" }).then(function (response) {
        updateActiveState(buttonEl, !bookmarked);
    })
}

function moreClicked(buttonEl, event) {
    var statusEl = buttonEl.parentElement.parentElement;
    var reblogStatusId = statusEl.getAttribute("data-status-id");
    var statusId = statusEl.getAttribute("data-visible-status-id");
    var statusAcct = statusEl.getAttribute("data-visible-status-acct");
    var isByMe = statusEl.getAttribute("data-visible-status-by-me") == "true";
    var isExpanded = statusEl.getAttribute("data-expanded") == "true";
    var showViewStatusId = true;  // cave.lls_getItem("show-view-status-id") == "true";

    promptSelect(
        [
            isByMe && ["delete", "Delete"],
            !isExpanded && ["expand", "Expand this post"],
            !isByMe && ["mention", "Mention " + "@" + statusAcct.split("@")[0]],
            showViewStatusId && ["id", "View status ID"]
        ],
        null
    ).then(function(result) {
        if (result == null) return;

        if (result == "delete") {
            var confirmResult = cave.dialog_twoButton(
                "",
                "Are you sure you want to delete this post?",
                "\uE001 Cancel",
                "\uE003 Delete"
            );
            if (confirmResult != 1) return;
            cave.dialog_beginWait(null, "Deleting...");

            (
                gfetch("/status/" + statusId + "/delete", { method: "POST" })
                .then(function(_) {
                    var matchingStatusEls = document.querySelectorAll("[data-visible-status-id='" + statusId + "']");
                    [].forEach.call(matchingStatusEls, function(matchingStatusEl) {
                        matchingStatusEl.parentNode.removeChild(matchingStatusEl);
                    });
                })
                ["finally"](function(_) {
                    cave.dialog_endWait();
                })
            )
        } else if (result == "expand") {
            navigate(makeURL("/status/" + statusId));
        } else if (result == "mention") {
            navigate(makeURL("/new", {"default_content": "@" + statusAcct + " "}));
        } else if (result == "id") {
            var description;
            if (reblogStatusId != statusId) {
                description = "Reblog: " + reblogStatusId + "\n" + "Original: " + statusId;
            } else {
                description = "ID: " + statusId;
            }

            cave.dialog_oneButtonAlignL(
                "",
                description,
                "\uE000 ty :3"
            );
        }
    });
}

function altClicked(buttonEl, event) {
    event.preventDefault();
    event.stopPropagation();
    cave.snd_playSe("SE_OLV_OK");

    var imageEl = buttonEl.parentElement;
    var alt = imageEl.getAttribute("alt");
    cave.dialog_oneButton(
        "", alt, "\uE000 OK"
    )
}

function spoilerClicked(buttonEl, event) {
    cave.snd_playSe("SE_OLV_OK");
    var statusEl = buttonEl.parentElement.parentElement;
    var statusContentEl = statusEl.getElementsByClassName("status__content")[0];

    if (statusContentEl.style.display == "none") {
        statusContentEl.style.display = "";
        buttonEl.innerText = "Hide"
    } else {
        statusContentEl.style.display = "none";
        buttonEl.innerText = "Show"
    }
}

function filterShowClicked(buttonEl, event) {
    cave.snd_playSe("SE_OLV_OK");
    var filterEl = buttonEl.parentElement;
    var statusId = filterEl.getAttribute("data-status-id");

    var statusEl = document.getElementById("status-" + statusId);

    filterEl.style.display = "none";
    statusEl.style.display = "";
}

function hideClicked(buttonEl, event) {
    cave.snd_playSe("SE_OLV_OK");
    var statusEl = buttonEl.parentElement.parentElement;
    var statusId = statusEl.getAttribute("data-status-id");

    var filterEl = document.getElementById("status-" + statusId + "-filter");
    filterEl.style.display = "";
    statusEl.style.display = "none";
}

function hasSeenHints() {
    var rawValue = cave.lls_getItem("hints");
    return rawValue && rawValue != "{}";
}

function resetHints() {
    cave.lls_setItem("hints", "{}");
}

function showOneTimeHint(id, message) {
    if (cave.lls_getItem("disable-hints") == "true") {
        return;
    }

    var rawValue = cave.lls_getItem("hints");
    var value = rawValue ? JSON.parse(rawValue) : {}
    var seenBefore = id in value;
    if (seenBefore) return;
    cave.dialog_oneButton("", message, "\uE000 thanks ^_^");
    value[id] = true;
    cave.lls_setItem("hints", JSON.stringify(value));
}

function doReblogFlow(
    buttonEl,
    statusId,
    statusText,
    statusAccount,
    reblogVisibility
) {
    if (statusText.length > 100) {
        statusText = statusText.slice(0, 100) + "..."
    }

    var description = "Post by @" + statusAccount + ":\n\n" + statusText;

    var title = "";
    if (reblogVisibility) {
        title = "Visibility: " + visibilityLabels[reblogVisibility];
    }

    var dialogResult = cave.dialog_twoButtonAlignL(
        title,
        description,
        "\uE001 Cancel",
        "\uE000 Boost"
    );

    if (dialogResult != 1) return;

    gfetch("/status/" + statusId + "/reblog" + (reblogVisibility ? ("?visibility=" + reblogVisibility) : ""), {method: "POST"}).then(function() {
        updateActiveState(buttonEl, true);
    });
}

function doUnreblogFlow(
    buttonEl,
    statusId,
    statusText,
    statusAccount
) {
    if (statusText.length > 100) {
        statusText = statusText.slice(0, 100) + "..."
    }

    var description = "Post by @" + statusAccount + ":\n\n" + statusText;

    var dialogResult = cave.dialog_twoButtonAlignL(
        "",
        description,
        "\uE001 Cancel",
        "\uE000 Unboost"
    );

    if (dialogResult != 1) return;

    gfetch("/status/" + statusId + "/unreblog", {method: "POST"}).then(function() {
        updateActiveState(buttonEl, false);
    });
}

function reblogClicked(buttonEl, event) {
	var reblogged = getActiveState(buttonEl);

	var statusEl = buttonEl.parentElement.parentElement
	var statusId = statusEl.getAttribute("data-visible-status-id");
	var statusText = statusEl.getElementsByClassName("status__content-text")[0].textContent;
	var statusAcct = statusEl.getAttribute("data-visible-status-acct");

	if (reblogged) {
        cave.snd_playSe("SE_OLV_OK");
        doUnreblogFlow(buttonEl, statusId, statusText, statusAcct);
	} else {
		showOneTimeHint(
				"boostVisibility",
				"Hint: Hold \uE005 while pressing Boost to set the post visibility of your boost! (You can also configure this to happen every time in the Settings.)"
		);

		if (isKeyDown("R") || cave.lls_getItem("ask-boost-visibility") == "true") {
			promptSelect(
				[
				    ["Boost visibility", [
                        ["public", visibilityLabels["public"]],
                        ["unlisted", visibilityLabels["unlisted"]],
                        ["private", visibilityLabels["private"]]
					]]
				],
				"public"
            ).then(function(result) {
                if (result == null) return;
                doReblogFlow(buttonEl, statusId, statusText, statusAcct, result);
            });
		} else {
			doReblogFlow(buttonEl, statusId, statusText, statusAcct, null);
		}
	}
}

function replyClicked(buttonEl, event) {
    cave.snd_playSe("SE_OLV_OK");
    var statusEl = buttonEl.parentElement.parentElement
    var statusId = statusEl.getAttribute("data-visible-status-id");
    navigate(makeURL("/new", {reply_to: statusId}));
}

init();