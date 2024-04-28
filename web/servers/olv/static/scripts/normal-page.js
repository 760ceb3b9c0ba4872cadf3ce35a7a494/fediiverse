function init() {
    cave.snd_playBgm("BGM_CAVE_SYOKAI")

    var returnScrollHeight = cave.ls_getItem("returnScrollHeight");
    if (returnScrollHeight) {
        cave.brw_scrollImmediately(0, parseInt(returnScrollHeight))
        cave.ls_removeItem("returnScrollHeight");
    } else {
        cave.brw_scrollImmediately(0, 0);
    }
};

document.addEventListener("DOMContentLoaded", function(event) {
    cave.dialog_endWait();
    setTimeout(cave.transition_end, 1000);
});

function previewImage(src, statusId) {
    cave.transition_begin();
    cave.ls_setItem("returnScrollHeight", cave.brw_getScrollTopY().toString());
    document.location = "/mediaPreview?url=" + encodeURIComponent(src);
}

function promptLink(href) {
    var dialogResult = cave.dialog_twoButton("", href, " Cancel", " Open");
    if (dialogResult == 1) {
        cave.jump_toWebbrs(href)
    }
}

function getActiveState(actionEl) {
    return actionEl.getAttribute("data-active") == "true";
}

function updateActiveState(actionEl, active) {
    var icon = actionEl.getAttribute("data-icon");
    var activeIcon = actionEl.getAttribute("data-active-icon");
    var iconEl = actionEl.getElementsByTagName("img")[0];

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

    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", function() {
        if (xhr.status < 200 || xhr.status >= 300) return;
        updateActiveState(buttonEl, !favourited);
    });
    xhr.open(
        "POST",
        "/status/" + statusId + (favourited ? "/unfavourite" : "/favourite")
    );
    xhr.send();
}

function bookmarkClicked(buttonEl, event) {
    var bookmarked = getActiveState(buttonEl);
    var statusEl = buttonEl.parentElement.parentElement
    var statusId = statusEl.getAttribute("data-visible-status-id");

    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", function() {
        if (xhr.status < 200 || xhr.status >= 300) return;
        updateActiveState(buttonEl, !bookmarked);
    });
    xhr.open(
        "POST",
        "/status/" + statusId + (bookmarked ? "/unbookmark" : "/bookmark")
    );
    xhr.send();
}

function promptSelect(choices, callback) {
    // lol this is a massive hack. read thru and ull see how funny this shit is
    // choices should be a list like this:
    /*
    [
        ["value", "Label"],
        ["value2", "Label2"]
    ]
    */
    // callback is (value: string | null) => void, value is null if cancelled

    var scrollY = cave.brw_getScrollTopY();
    var targetPos = scrollY + 400;

    var selectEl = document.createElement("select");
    selectEl.style.position = "absolute";
    selectEl.style["-webkit-appearance"] = "none";
    selectEl.style.top = targetPos + "px";
    selectEl.style.left = "0px";
    selectEl.style.width = "1px";
    selectEl.style.height = "1px";
    // selectEl.style.display = "none";
    selectEl.style.opacity = "0";

    for (var index = 0; index < choices.length; index++) {
        var choice = choices[index];
        var optionEl = document.createElement("option");
        optionEl.setAttribute("value", choice[0]);
        optionEl.innerText = choice[1];
        selectEl.appendChild(optionEl);
    }

    document.body.appendChild(selectEl);

    // will refocus this later:
    var rnActiveElement = document.activeElement;
    cave.select_setClosingCallback(function(index) {
        cave.select_resetClosingCallback();
        selectEl.remove();
        if (rnActiveElement) {
            rnActiveElement.focus();
        }
        // THE WOKE!

        if (index == -1) {
            callback(null);
        } else {
            callback(choices[index][0]);
        }
    });

    // opening the choice will block keyup events, so we assume all buttons are immediately released when the dialog starts.
    forceAllKeysDown();

    cave.sendMouseClick(0, targetPos);
}

function altClicked(buttonEl, event) {
    event.preventDefault();
    event.stopPropagation();

    var imageEl = buttonEl.parentElement;
    var alt = imageEl.getAttribute("alt");
    cave.dialog_oneButton(
        "", alt, " OK"
    )
}

function spoilerClicked(buttonEl, event) {
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
    var filterEl = buttonEl.parentElement;
    var statusId = filterEl.getAttribute("data-status-id");

    var statusEl = document.getElementById("status-" + statusId);

    filterEl.style.display = "none";
    statusEl.style.display = "";
}

function hideClicked(buttonEl, event) {
    var statusEl = buttonEl.parentElement.parentElement;
    var statusId = statusEl.getAttribute("data-status-id");

    var filterEl = document.getElementById("status-" + statusId + "-filter");
    filterEl.style.display = "";
    statusEl.style.display = "none";
}

function showOneTimeHint(id, message) {
    var seenBefore = cave.lls_getItem("hint_" + id) == "true";
    if (seenBefore) return;

    cave.dialog_oneButton("", message, "thx >w<");
    cave.lls_setItem("hint_" + id, "true");
}

var visibilityLabels = {
    public: "Public",
    unlisted: "Quiet public",
    private: "Followers"
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
        " Cancel",
        " Boost"
    );

    if (dialogResult != 1) return;

    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", function() {
        if (xhr.status < 200 || xhr.status >= 300) return;
        updateActiveState(buttonEl, true);
    });
    xhr.open("POST", "/status/" + statusId + "/reblog" + (
        reblogVisibility ? ("?visibility=" + reblogVisibility) : ""
    ));
    xhr.send();
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
        " Cancel",
        " Unboost"
    );

    if (dialogResult != 1) return;

    var xhr = new XMLHttpRequest();
    xhr.addEventListener("load", function() {
        if (xhr.status < 200 || xhr.status >= 300) return;
        updateActiveState(buttonEl, false);
    });
    xhr.open("POST", "/status/" + statusId + "/unreblog");
    xhr.send();
}

function reblogClicked(buttonEl, event) {
    var reblogged = getActiveState(buttonEl);

    var statusEl = buttonEl.parentElement.parentElement
    var statusId = statusEl.getAttribute("data-visible-status-id");
    var statusText = statusEl.getElementsByClassName("status__content-text")[0].textContent;
    var statusAcct = statusEl.getAttribute("data-visible-status-acct");

    if (reblogged) {
        doUnreblogFlow(buttonEl, statusId, statusText, statusAcct);
    } else {
        showOneTimeHint(
            "boostVisibility",
            "hint: hold  while clicking the Boost icon to set the visibility of your boost!"
        );

        if (isKeyDown("R")) {
            promptSelect(
                [
                    ["public", visibilityLabels["public"]],
                    ["unlisted", visibilityLabels["unlisted"]],
                    ["private", visibilityLabels["private"]]
                ],
                function(result) {
                    if (result == null) return;
                    doReblogFlow(buttonEl, statusId, statusText, statusAcct, result);
                }
            );
        } else {
            doReblogFlow(buttonEl, statusId, statusText, statusAcct, null);
        }
    }
}

init();