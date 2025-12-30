var titleId = "000400000A32F100"  // title ID of fediiverse Setup Utility

cave.snd_stopBgm(0);
cave.transition_end();
cave.dialog_endWait();
cave.toolbar_setVisible(false);


function launch() {
    cave.snd_playSe("SE_OLV_OK");
    // 0 = do not ask before jumping
    cave.jump_toApplication(0, titleId);
}

document.addEventListener("DOMContentLoaded", function() {
    cave.snd_playSe("SE_CTR_COMMON_NOTICE");
    var button = document.getElementById("launch");
    if (!cave.jump_existsApplication(titleId)) {
        button.disabled = true;
    }
})