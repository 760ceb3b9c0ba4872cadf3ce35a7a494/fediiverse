cave.requestGc();

var canGoBack = cave.history_getBackCount() > 0;
var pathname = document.location.pathname;

cave.toolbar_enableBackBtnFunc(false );
cave.toolbar_setVisible(true);
cave.toolbar_setMode(0);
cave.home_setEnabled(true); /* default to home button enabled */

if (canGoBack) {
    cave.toolbar_setButtonType(1);
} else {
    cave.toolbar_setButtonType(0);
}

cave.toolbar_setWideButtonMessage("???");


cave.toolbar_setCallback(1, function() {
    if (canGoBack) {
        cave.transition_begin();
        history.back();
    } else {
        cave.exitApp();
    }
});

cave.toolbar_setCallback(3, function() {
    cave.transition_begin();
    if (pathname == "/timeline") {
        window.location.replace("/timeline?kind=home");
    } else {
        window.location.assign("/timeline?kind=home");
    }
});

if (pathname == "/timeline") {
    cave.toolbar_setActiveButton(3);
}