function hasCurrentSketch() {
	return !!(document.querySelector("#sketch").value);
}

function hasCurrentContent() {
	return !!(document.querySelector("#content").value);
}

function clearSketch() {
	document.querySelector("#sketch").value = "";
}

function isValid() {
	return hasCurrentSketch() || hasCurrentContent() || hasCurrentScreenshot();
}

function checkCanExitPage() {
    if (hasCurrentSketch() || hasCurrentContent() || hasCurrentContentWarning()) {
        return false;
    }
    return true;
}

function updateCanExitPage() {
    var canExitPage = checkCanExitPage();
    if (cave.lls_getItem("disable-home-safety") == "true") {
        cave.home_setEnabled(true);
    } else {
        cave.home_setEnabled(canExitPage);
    };
    if (canExitPage) {
        window.beforeExitMessage = undefined;
    } else {
        window.beforeExitMessage = "Are you sure you want to discard this post?";
    }
}

function updateSketchButton() {
	var sketchButtonEl = document.querySelector("#new__sketch-button");
	var iconEl = sketchButtonEl.querySelector(".icon");

	if (hasCurrentSketch()) {
		sketchButtonEl.setAttribute("data-active", "true");
	} else {
		sketchButtonEl.setAttribute("data-active", "false");
	}
}

function editSketch() {
	var sketchInputEl = document.querySelector("#sketch");
	var sketchButtonEl = document.querySelector("#new__sketch-button");
	var oldSketchData = null;

	if (sketchInputEl.value) {
		cave.memo_setImageBmp(sketchInputEl);
	} else {
		cave.memo_clear();
		oldSketchData = cave.memo_getImageBmp();
	}

	cave.memo_open();
	if (!cave.memo_hasValidImage()) return;
	var data = cave.memo_getImageBmp();
	if (data == oldSketchData) return;
	sketchInputEl.value = data;
}

function onSketchButtonClicked() {
    cave.snd_playSe("SE_OLV_OK");
	if (hasCurrentSketch()) {
		// if there is a current sketch, show Edit/Clear dialog
		promptSelect(
			[
				["edit", "Edit sketch"],
				["clear", "Clear sketch"],
			],
			"edit"
        ).then(function(result) {
            if (result == null) return;

            if (result == "edit") {
                editSketch();
            } else if (result == "clear") {
                clearSketch();
            }

            updateSketchButton();
    		updateCanExitPage();
        });
	} else {
		// if theres not then they just edit it
		editSketch();
		updateSketchButton();
		updateCanExitPage();
	}
}

var visibilityIcons = {
	public: "earth",
	unlisted: "moon",
	private: "lock",
	direct: "at"
};

function updateVisibilityButton() {
	var visibilityValue = document.querySelector("#visibility").value;
	var visibilityButtonEl = document.querySelector("#new__visibility-button");
	var iconEl = visibilityButtonEl.querySelector(".icon");

	visibilityButtonEl.querySelector("span").textContent = visibilityLabelsShort[visibilityValue];
	iconEl.setAttribute("icon", visibilityIcons[visibilityValue]);
};

function changeVisibility() {
	var visibilityValue = document.querySelector("#visibility").value;
    promptSelect(
        [
            ["public", visibilityLabels["public"]],
            ["unlisted", visibilityLabels["unlisted"]],
            ["private", visibilityLabels["private"]],
            ["direct", visibilityLabels["direct"]],
        ],
        visibilityValue
    ).then(function(newValue) {
        if (newValue == null) return;

        document.getElementById("visibility").value = newValue;
        updateVisibilityButton();
		updateCanExitPage();
    });
}

function hasCurrentScreenshot() {
	return !!(document.querySelector("form").querySelector(".screenshot-form-field"))
}

function updateScreenshotButton() {
	document.querySelector("#new__screenshot-button").setAttribute("data-active", hasCurrentScreenshot() ? "true" : "false");
}

function addScreenshotToForm() {
	if (hasCurrentScreenshot()) return;
	var formEl = document.querySelector("form");

	try {
		function addElForLlsKey(llsKey) {
			var inputEl = document.createElement("input");
			inputEl.setAttribute("name", llsKey);
			inputEl.setAttribute("class", "screenshot-form-field");
			inputEl.setAttribute("type", "file");
			inputEl.setAttribute("lls", llsKey);
			formEl.appendChild(inputEl);
			// yes its an insane hack and its NINTENDO THAT DID THIS NOT ME
			inputEl.focus();
			inputEl.click();
			inputEl.blur();
			inputEl.style.display = "none";
		};
		addElForLlsKey("capture_bottom");
		addElForLlsKey("capture_top");
		// addElForLlsKey("capture_top_left_eye");
		// addElForLlsKey("capture_top_right_eye");
	} catch (e) {
		alert(e);
	}
}

function removeScreenshotFromForm() {
	[].forEach.call(document.querySelectorAll(".screenshot-form-field"), function(el) {
		el.parentElement.removeChild(el);
	});
}

function doAddScreenshotPrompt() {
	cave.transition_beginWithoutEffect();

	var top = document.createElement("div");
	top.style.display = "-webkit-box";
	top.style.position = "absolute";
	top.style.left = "0px";
	top.style.right = "0px";
	top.style.height = "240px";
	top.style.width = "400px";
	top.style.paddingTop = "20px";
	top.style.backgroundColor = "rgba(0, 0, 0, 0.915)";
	top.style.zIndex = 101;
	top.style["-webkit-box-orient"] = "vertical";
	top.style["-webkit-box-align"] = "center";
	top.style["-webkit-box-pack"] = "center";

	sleep(70)
	.then(function() {
		return new Promise(function(resolve) {
			var img1 = document.createElement("img");
			img1.setAttribute("src", cave.lls_getPath("capture_top"));
			img1.style.background = "#EEE";
			img1.style.display = "block";
			img1.style.height = "105px";
			img1.addEventListener("load", function() {resolve(top)})
			top.appendChild(img1);

			var img2 = document.createElement("img");
			img2.setAttribute("src", cave.lls_getPath("capture_bottom"));
			img2.style.background = "#EEE";
			img2.style.display = "block";
			img2.style.height = "105px";
			img2.addEventListener("load", function() {resolve(top)})
			top.appendChild(img2);
		})
	})
	.then(function() {
		var y = cave.brw_getScrollTopY();
		top.style.top = y - 20 + "px";
		document.body.appendChild(top);
	})
	.then(function() { return sleep(50); })
	.then(function() {
		var text = (
			cave.sap_exists()
			? "Attach a screenshot of " + cave.sap_longTitle() + "?"
			: "Attach a screenshot?"
		)

		return cave.dialog_twoButton(
			"",
			text,
			"\uE001 Cancel",
			"\uE000 Attach"
		);
	})
	.then(function(dialogResult) {
		if (dialogResult) {
			addScreenshotToForm();
			updateScreenshotButton();
		}
	})
	["finally"](function() {
		cave.transition_endWithoutEffect();
		document.body.removeChild(top);
		document.querySelector("#new__screenshot-button").focus();
	});
}

function onScreenshotButtonClicked() {
	if (!hasCurrentScreenshot()) {
		doAddScreenshotPrompt();
	} else {
		if (cave.dialog_twoButton(
			"",
			"Remove this screenshot?",
			"\uE001 Cancel",
			"\uE000 Remove"
		)) {
			removeScreenshotFromForm();
			updateScreenshotButton();
		}
	}
}

function initCapture() {
	cave.lls_setCaptureImage("capture_bottom", 0);
    // cave.lls_setCaptureImage("capture_top_left_eye", 1);
    // cave.lls_setCaptureImage("capture_top_right_eye", 2);
    cave.lls_setCaptureImage("capture_top", 3);
}

document.addEventListener("DOMContentLoaded", function() {
	updateVisibilityButton();
    updateCanExitPage();

	var formEl = document.querySelector(".new");

	formEl.addEventListener("beforesubmit", function(event) {
	    // nothing.
	})

	formEl.addEventListener("submit", function(event) {
		if (!isValid()) {
			cave.dialog_oneButton("", "Your post can't be empty!", "\uE000 Got it");
			event.preventDefault();
			return;
		}

		cave.dialog_beginWait(null, "Posting...");
	});

	var postButtonEl = document.querySelector("#new__post-button");
	postButtonEl.addEventListener("click", function() {
        cave.snd_playSe("SE_OLV_OK");
	})

	var contentEl = document.querySelector("#content");
	contentEl.addEventListener("change", function() {
	    updateCanExitPage();
	})

	// make sure we actually scroll to the right position, because brw_scrollImmediately does nothing until something loads. idk what.
	var intervalId = setInterval(function() {
		cave.brw_scrollImmediately(0, formEl.offsetTop);
		if (cave.brw_getScrollTopY() > 0) clearInterval(intervalId);
	}, 33);

    var screenshotButtonEl = document.querySelector("#new__screenshot-button");
	var enableCapture = (
		cave.lls_getItem("always-allow-capture") == "true"
		? true
		: cave.sap_exists()  // only if a suspended application exists
	)

	if (enableCapture) {
		initCapture();
	} else {
		screenshotButtonEl.parentElement.removeChild(screenshotButtonEl);
	}

	var sapIconEl = document.querySelector("#sap-icon");
	var sapBubbleEl = document.querySelector("#sap-icon-bubble");
	if (cave.sap_exists()) {
		sapIconEl.src = "data:image/png;base64," + cave.sap_smallIconPng();
	} else {
		sapBubbleEl.parentElement.removeChild(sapBubbleEl);
	}
})

function hasCurrentContentWarning() {
	return !!(document.querySelector("#content_warning").value);
}

function updateContentWarningButton() {
	var buttonEl = document.querySelector("#new__content-warning-button");
	buttonEl.setAttribute("data-active", hasCurrentContentWarning() ? "true" : "false");
}

function onContentWarningButtonClicked() {
    cave.snd_playSe("SE_OLV_OK");
    var value = document.querySelector("#content_warning").value;

    var result = cave.swkbd_callFullKeyboard(
        value || "",
        100,  // maxLength  (i just picked a random value idk)
        0,  // minLength
        false,  // isMonospace
        false,  // isMultiline
        true  // isConvertible (whats that mean ?) (oh it means it shows the dictionary word list thing)
    );
    if (result != null) {
        document.querySelector("#content_warning").value = result;
    }

    updateContentWarningButton();
    updateCanExitPage();
}