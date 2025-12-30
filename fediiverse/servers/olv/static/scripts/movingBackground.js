var boundToFramerate = true;  // two ways to do the background
var pos = 0;

function startMoving() {
    return setInterval(function() {
        if (boundToFramerate) {
            pos = (pos + 1);
            if (pos >= 88) pos = 0;
        } else {
            pos = Date.now() / 120 % 88;
        }
        document.body.style.backgroundPosition = "" + pos + "px " + pos + "px";
    }, 33.333333);
}

if (cave.lls_getItem("disable-animated-checkerboard") != "true") {
    startMoving();
}

