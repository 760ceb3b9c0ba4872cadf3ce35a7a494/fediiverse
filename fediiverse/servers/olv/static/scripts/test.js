function initSTable(tableType) {
    var table = document.getElementById(tableType);
    var getCount = cave[tableType + "_getCount"];
    var getKeyAt = cave[tableType + "_getKeyAt"];
    var getItem = cave[tableType + "_getItem"];

    for (var i = 0; i < getCount(); i++) {
        var key = getKeyAt(i);
        var value = getItem(key);
        var tr = document.createElement("tr");

        var td_index = document.createElement("td");
        td_index.innerText = i;
        tr.appendChild(td_index);

        var td_key = document.createElement("td");
        td_key.innerText = key;
        tr.appendChild(td_key);

        var td_value = document.createElement("td");
        if (key == "token") {
            td_value.innerHTML = "<i>token hidden</i>"
        } else {
            td_value.innerText = value;
        }
        tr.appendChild(td_value);

        table.appendChild(tr);
    }
}

function initSfxTable() {
    var table = document.getElementById("sfx");
    var list = [
        "OLV_CANCEL",
        "OLV_OK",
        "OLV_OK_SUB",
        "OLV_CHECKBOX_CHECK",
        "OLV_CHECKBOX_UNCHECK",
        "OLV_MII_ADD",
        "OLV_RELOAD",
        "OLV_BALLOON_OPEN",
        "OLV_BALLOON_CLOSE",
        "WAVE_SCROLL_PAGE",
        "WAVE_SCROLL_PAGE_LR",
        "WAVE_SCROLL_LIMIT_LR",
        "CTR_COMMON_TOUCH",
        "CTR_COMMON_TOUCHOUT",
        "CTR_COMMON_TOUCHOUT_S",
        "CTR_COMMON_TOUCHIN",
        "CTR_COMMON_TOGGLE",
        "CTR_COMMON_SILENT",
        "CTR_COMMON_BUTTON",
        "CTR_COMMON_OK",
        "CTR_COMMON_RETURN",
        "CTR_COMMON_CANCEL",
        "CTR_COMMON_WAIT",
        "CTR_COMMON_WAIT_END",
        "CTR_COMMON_CONNECT",
        "CTR_COMMON_ERROR",
        "CTR_COMMON_NOTICE",
        "CTR_COMMON_NOMOVE",
        "CTR_COMMON_SCROLL",
        "CTR_COMMON_SCROLL_LIST",
        "CTR_COMMON_SCROLL_TEXT",
        "CTR_COMMON_SCROLL_END",
        "CTR_COMMON_DIALOG",
        "CTR_COMMON_SYSAPPLET_END",
        "CTR_SPIDER_HG_Prev",
        "CTR_SPIDER_HG_Next",
        "CTR_SPIDER_MV_START",
        "CTR_SPIDER_LINK",
        "CTR_SPIDER_YOMIKOMI",
        "CTR_SPIDER_YOMIEND",
        "CTR_SPIDER_YomiCancel",
        "CTR_SPIDER_MV_KAKTEI",
        "CTR_SPIDER_MV_LINE",
        "CTR_SPIDER_MV_CURSOR",
        "CTR_SPIDER_FavCursor",
        "CTR_SPIDER_Navi",
        "CTR_SPIDER_Navi_On",
        "CTR_SPIDER_Navi_Off",
        "CTR_SPIDER_ZOOM2BIG",
        "CTR_SPIDER_ZOOM2SMALL",
        "CTR_SPIDER_LINK_CLICK",
        "CTR_SPIDER_BTN_CLICK",
        "CTR_SPIDER_Ticker",
        "CTR_SPIDER_SEL_START",
        "CTR_SPIDER_SEL_CURSOR",
        "CTR_SPIDER_InfoOn",
        "CTR_SPIDER_SEL_END"
    ];

    list.forEach(function(name) {
        var tr = document.createElement("tr");

        var td_name = document.createElement("td");
        td_name.innerText = name;
        tr.appendChild(td_name);

        var td_play = document.createElement("td");
        var button = document.createElement("button");
        button.addEventListener("click", function() {
            cave.snd_playSe("SE_" + name);
        });
        button.innerText = "Play";
        td_play.appendChild(button);
        tr.appendChild(td_play);
        table.appendChild(tr);
    })
}

function initBgmTable() {
    var table = document.getElementById("bgm");
    var list = [
        "CAVE_MAIN",
        "CAVE_MAIN_2",
        "CAVE_MAIN_LOOP",
        "CAVE_MAIN_LOOP_NOWAIT",
        "CAVE_WORLD_MAP_MINT",
        "CAVE_WORLD_MAP",
        "CAVE_MAIN_OFFLINE",
        "CAVE_SETTING",
        "CAVE_SYOKAI",
        "CAVE_SYOKAI2"
    ];

    list.forEach(function(name) {
        var tr = document.createElement("tr");

        var td_name = document.createElement("td");
        td_name.innerText = name;
        tr.appendChild(td_name);

        var td_play = document.createElement("td");
        var button = document.createElement("button");
        button.addEventListener("click", function() {
            cave.snd_stopBgm(0);
            cave.snd_playBgm("BGM_" + name);
        });
        button.innerText = "Play";
        td_play.appendChild(button);
        tr.appendChild(td_play);
        table.appendChild(tr);
    })
}

function addRow(tb, k, v, className) {
	var tr = document.createElement("tr");
	var td_name = document.createElement("td");
	td_name.innerText = k;
	tr.appendChild(td_name);

	var td_value = document.createElement("td");
	if (typeof v == "string") {
		td_value.innerText = v;
	} else {
		td_value.appendChild(v);
	}
	tr.appendChild(td_value);
	if (className) {
		tr.setAttribute("class", className);
	}
	tb.appendChild(tr);
}

function initMiiTable() {
    var table = document.getElementById("mii");

    addRow(table, "Name", cave.mii_getName());
    addRow(table, "Is registered", cave.mii_isRegistered().toString());

    var moods = ["Normal", "Happy", "Like", "Surprised", "Frustrated", "Puzzled"]
    for (var i = 0; i < moods.length; i++) {
        var iconDataUri = cave.mii_getIconBase64(i);
        var img = document.createElement("img");
        img.src = iconDataUri;
        addRow(table, moods[i], img, "mood-row");
    }
}

function initHistoryTable() {
    var table = document.getElementById("history");

    // this regex seems to work ok:
    var exp = /token=.+?(?=[&?]|$)/m;

    for (var i = 0; i < cave.history_getBackCount(); i++) {
        var url = cave.history_getAt(i);
        url = url.replace(exp, "token=[...]");

        var tr = document.createElement("tr");

        var td_index = document.createElement("td");
        td_index.innerText = i;
        tr.appendChild(td_index);

        var td_value = document.createElement("td");
        td_value.innerText = url;
        tr.appendChild(td_value);

        table.appendChild(tr);
    }
}

function initCaptureTable() {
    cave.lls_setCaptureImage("capture_bottom", 0);
    cave.lls_setCaptureImage("capture_top_left_eye", 1);
    cave.lls_setCaptureImage("capture_top_right_eye", 2);
    var table = document.getElementById("capture");
    addRow(table, "e", cave.capture_isEnabled().toString());
    addRow(table, "e 0", cave.capture_isEnabledEx(0).toString());
    addRow(table, "e 1", cave.capture_isEnabledEx(1).toString());
    addRow(table, "e 2", cave.capture_isEnabledEx(2).toString());

	var img = document.createElement("img");
	img.src = cave.lls_getPath("capture_top_left_eye");
    addRow(table, "Left", img);

	var img = document.createElement("img");
	img.src = cave.lls_getPath("capture_top_right_eye");
    addRow(table, "Right", img);

	var img = document.createElement("img");
	img.src = cave.lls_getPath("capture_bottom");
	document.body.appendChild(img);
    addRow(table, "Bottom", img);
}

function initSapTable() {
    var table = document.getElementById("sap");
    var exists = cave.sap_exists();
    addRow(table, "Exists",  exists.toString());
    if (exists) {
		addRow(table, "Program ID", cave.sap_programId());
		addRow(table, "Short title", cave.sap_shortTitle());
		addRow(table, "Long title", cave.sap_longTitle());
		addRow(table, "Publisher", cave.sap_publisher());
		var smallImg = document.createElement("img");
		smallImg.src = "data:image/png;base64," + cave.sap_smallIconPng();
		addRow(table, "Small icon", smallImg);

		var largeImg = document.createElement("img");
		largeImg.src = "data:image/png;base64," + cave.sap_largeIconPng();
		addRow(table, "Large icon", largeImg);

		var close = document.createElement("button");
    }
}

function main() {
    initSTable("ls");
    initSTable("lls");
    initSfxTable();
    initBgmTable();
    initMiiTable();
    initCaptureTable();
    initSapTable();
    initHistoryTable();
}

document.addEventListener("DOMContentLoaded", main)