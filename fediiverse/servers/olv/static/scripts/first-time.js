cave.snd_stopBgm(0);
cave.transition_end();
cave.dialog_endWait();
cave.toolbar_setVisible(false);

function getStarted() {
    cave.snd_playSe("SE_OLV_OK");
    cave.dialog_beginWait();
    cave.lls_setItem("first-time-complete", "true");
    navigate(makeURL("/timeline", {kind: "home"}), true);
}

document.addEventListener("DOMContentLoaded", function() {
    cave.snd_playBgm("BGM_CAVE_SYOKAI2");
    var button = document.getElementById("launch");
})