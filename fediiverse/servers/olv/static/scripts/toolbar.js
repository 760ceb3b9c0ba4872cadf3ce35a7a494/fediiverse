function waitForPageLoad() {
    return new Promise(function(resolve) {
        if (document.readyState === "complete") resolve();
        document.addEventListener("load", function() {
            resolve();
        })
    });
}

document.addEventListener("DOMContentLoaded", function(event) {
    cave.dialog_endWait();
    setTimeout(cave.transition_end, 500);
});

var canGoBack = cave.history_getBackCount() > 1;  // greater than 1 instead of gt 0 because the first page redirect creates a history state
var pathname = document.location.pathname;

cave.toolbar_enableBackBtnFunc(true);  // makes the B button work to go back
cave.toolbar_enableBackBtnKeyAnim(true);
cave.toolbar_setVisible(true);
cave.toolbar_setMode(0);
cave.home_setEnabled(true); /* default to home button enabled */
cave.toolbar_setNotificationCount(0);

if (canGoBack) {
	cave.toolbar_setButtonType(1);  // back button
} else {
	cave.toolbar_setButtonType(0);  // X home button
}

cave.toolbar_setWideButtonMessage("???");


cave.toolbar_setCallback(1, function() {
	if (canGoBack) {
        cave.transition_begin();
        waitForPageLoad.then(function() {
            history.back();
        });
	} else if (cave.jump_suspendedApplication()) {
		cave.jump_toSuspendedApplication();
	} else {
		cave.exitApp();
	}
});

cave.toolbar_setCallback(3, function() {
    var currentTimelineKind = document.documentElement.getAttribute("data-timeline-kind");

	promptSelect(
	    [
	        ["home", "Home timeline"],
	        ["trending", "Trending timeline"],
	        ["local", "Local timeline"],
	        ["federated", "Federated timeline"],
	    ],
	    currentTimelineKind
	).then(function(kind) {
	    if (!kind) return;
	    if (!ensureCanNavigate()) return;
        cave.toolbar_setActiveButton(3);
        navigate(makeURL("/timeline", {kind: kind}), pathname == "/timeline");
	})
});

cave.toolbar_setCallback(2, function() {
	if (!ensureCanNavigate()) return;
    cave.toolbar_setActiveButton(2);
	navigate(makeURL("/new"))
});

cave.toolbar_setCallback(5, function() {
	// go to my profile
		promptSelect(
	    [
	        ["profile", "My profile"],
	        ["settings", "Settings"]
	    ],
	    pathname == "/settings" ? "settings" : "profile"
	).then(function(kind) {
	    if (!kind) return;
	    if (!ensureCanNavigate()) return;
        cave.toolbar_setActiveButton(5);
        if (kind == "profile") {
        	navigate(makeURL("/profile/" + document.querySelector("html").getAttribute("data-local-user-id")));
        } else if (kind == "settings") {
            navigate(makeURL("/settings"));
        }
	})
});

cave.toolbar_setCallback(7, function() {
	// question mark button for guest mode;
	navigate(makeURL("/settings"));
})

cave.toolbar_setCallback(4, function() {
    cave.dialog_oneButton("", "Notifications are not supported yet, sorry! \uE00A", "\uE000 Okay");
});

// polyfill:
if (!String.prototype.startsWith) {
	Object.defineProperty(String.prototype, 'startsWith', {
		value: function(search, rawPos) {
			var pos = rawPos > 0 ? rawPos|0 : 0;
			return this.substring(pos, pos + search.length) === search;
		}
	});
}
// end polyfill


// check which button should be active:
document.addEventListener("DOMContentLoaded", function() {
	var profileEl = document.getElementsByClassName("profile")[0];
	if (pathname.startsWith("/profile") && profileEl.getAttribute("data-is-me") || pathname == "/settings") {
		cave.toolbar_setActiveButton(5);
	} else if (pathname == "/new") {
		cave.toolbar_setActiveButton(2);
	} else if (pathname == "/timeline") {
		cave.toolbar_setActiveButton(3);  // communities button
	} else {
		cave.toolbar_setActiveButton(-1);
	}
});