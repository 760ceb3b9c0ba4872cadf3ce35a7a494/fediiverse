function updateBgm(selectEl) {
    var value = selectEl.value;

    cave.lls_setItem("bgm", value);
    bgmFunc();
}

function checkboxSe(el) {
    if (el.checked) {
        cave.snd_playSe("SE_OLV_CHECKBOX_CHECK");
    } else {
        cave.snd_playSe("SE_OLV_CHECKBOX_UNCHECK");
    }
}

function updateAskBoostVisibility(checkboxEl) {
    checkboxSe(checkboxEl);
    cave.lls_setItem("ask-boost-visibility", checkboxEl.checked ? "true" : "false");
}

function updateHomeSafety(checkboxEl) {
    checkboxSe(checkboxEl);
    cave.lls_setItem("disable-home-safety", !checkboxEl.checked ? "true" : "false");
}

function updateShowHints(checkboxEl) {
    checkboxSe(checkboxEl);
    cave.lls_setItem("disable-hints", !checkboxEl.checked ? "true" : "false");
}

function triggerResetHints(buttonEl) {
    cave.snd_playSe("SE_OLV_OK");
    buttonEl.disabled = true;
    resetHints();
}

function updateAnimateCheckerboard(checkboxEl) {
    checkboxSe(checkboxEl);
    cave.lls_setItem("disable-animated-checkerboard", !checkboxEl.checked ? "true" : "false");
}

function updateShowViewStatusId(checkboxEl) {
    checkboxSe(checkboxEl);
    cave.lls_setItem("show-view-status-id", checkboxEl.checked ? "true" : "false");
}

function updateReloadBind(selectEl) {
    var value = selectEl.value;
    cave.lls_setItem("reload-bind", value);
}

function triggerLogout(buttonEl) {
    var confirmResult = cave.dialog_twoButton(
        "",
        "Are you sure you want to log out of fediiverse? Your settings will be lost.\nYou can log in again using the fediiverse Setup Utility.",
        "\uE001 Cancel",
        "\uE003 Log out"
    );
    if (confirmResult != 1) return;
    cave.snd_stopBgm(3000);
    cave.dialog_beginWait(null, "Logging out...");

    (
        gfetch("/logout", { method: "POST" })
        .then(function(_) {
            cave.home_setEnabled(false);
            cave.dialog_endWait();
            cave.dialog_oneButton("", "Logged out.\nThank you for using fediiverse!", "\uE000 Exit");
            cave.exitApp();
        })
        ["finally"](function(_) {
            cave.dialog_endWait();
            cave.home_setEnabled(true);
        })
    )
}

function updateAlwaysAllowCapture(checkboxEl) {
    checkboxSe(checkboxEl);
    cave.lls_setItem("always-allow-capture", checkboxEl.checked ? "true" : "false");
}

document.addEventListener("DOMContentLoaded", function() {
    document.getElementById("bgm").value = cave.lls_getItem("bgm");
    document.getElementById("ask-boost-visibility").checked = cave.lls_getItem("ask-boost-visibility") == "true";
    document.getElementById("home-safety").checked = cave.lls_getItem("disable-home-safety") != "true";
    document.getElementById("show-hints").checked = cave.lls_getItem("disable-hints") != "true";
    document.getElementById("reset-hints").disabled = !hasSeenHints();
    document.getElementById("animate-checkerboard").checked = cave.lls_getItem("disable-animated-checkerboard") != "true";
    // document.getElementById("show-view-status-id").checked = cave.lls_getItem("show-view-status-id") == "true";
    document.getElementById("reload-bind").value = cave.lls_getItem("reload-bind") || "L+R";
    document.getElementById("always-allow-capture").checked = cave.lls_getItem("always-allow-capture") == "true";
})

function initKeys() {
    function maybeTest() {
        if (isKeyDown("R") && isKeyDown("X")) {
            navigate(makeURL("/test"))
        }
    }

    addKeyEventListener("R", maybeTest);
    addKeyEventListener("X", maybeTest);
}