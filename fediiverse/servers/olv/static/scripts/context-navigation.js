function makeURL(path, params) {
	if (!params) params = {};
	params["token"] = cave.lls_getItem("token");

    var url = path;
	var first = true;
	for (var key in params) {
		if (first) {
			url += "?";
			first = false;
		} else {
			url += "&";
		}
		url += encodeURIComponent(key) + "=" + encodeURIComponent(params[key])
	}
	return url;
}

function navigate(url, replace) {
    if (!ensureCanNavigate()) return;
    cave.transition_begin();
	if (replace) { window.location.replace(url) }
	else { window.location.assign(url) }
}

function navigateWithToken(targetHref) {
    if (targetHref.indexOf("?") == -1) {
        targetHref += "?";
    } else {
        targetHref += "&";
    }

    targetHref += "token=";
    targetHref += cave.lls_getItem("token");

    navigate(targetHref);
}

function ensureCanNavigate() {
    if (window.beforeExitMessage) {
        var confirmResult = cave.dialog_twoButton(
            "",
            window.beforeExitMessage,
            "\uE001 Cancel",
            "\uE003 Confirm"
        );
        if (confirmResult == 1) {
            window.beforeExitMessage = undefined;
            return true;
        };
        return false;
    }
    return true;
}

document.addEventListener("DOMContentLoaded", function() {
	[].forEach.call(document.querySelectorAll("a[contextual]"), function(el) {
		el.addEventListener("click", function(event) {
		    event.preventDefault();
            if (!ensureCanNavigate()) return;
            navigateWithToken(el.getAttribute("href"));
		});
	});
})