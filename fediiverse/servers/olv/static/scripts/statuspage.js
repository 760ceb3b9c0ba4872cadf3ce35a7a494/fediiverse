document.addEventListener("DOMContentLoaded", function() {
    var mainStatus = document.querySelector(".main-status");
    var negY = 232;  // 12 to show the post in the top screen, 232 for the bottom screen
    var targetOffset = mainStatus.offsetTop - negY;

    var intervalId = setInterval(function() {
		cave.brw_scrollImmediately(0, targetOffset);
		if (cave.brw_getScrollTopY() >= targetOffset) clearInterval(intervalId);
	}, 33);
})