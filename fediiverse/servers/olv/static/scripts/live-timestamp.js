function formatTimedeltaShort(timedelta) {
	// mirrors format_timedelta_short
	useMonths = true;

	var delta = {
        seconds: timedelta / 1000,
        days: timedelta / 1000 / 60 / 60 / 24
	}

	var years = Math.floor(delta.days / 365);
	var days = Math.floor(delta.days % 365);
	var numMonths = Math.floor(days / 30.5);

	if ((years == 0) && (days < 1)) {
		if (delta.seconds < 10) {
			return "now"
		}

		if (delta.seconds < 60) {
			seconds = Math.floor(delta.seconds);
			if (seconds == 1) return "1 second";
			return seconds + " seconds";
		}

		if (delta.seconds < 3600) {
			minutes = Math.floor(delta.seconds / 60);
			if (minutes == 1) return "1 minute";
			return minutes + " minutes"
		}

		if (delta.seconds >= 3600) {
			hours = Math.floor(delta.seconds / 3600);
			if (hours == 1) return "1 hour";
			return hours + " hours"
		}
	} else if (years == 0) {
		if ((!useMonths) || (numMonths == 0)) {
		    if (days == 1) return "1 day";
			return days + " days";
		}

        if (numMonths == 1) return " 1 month";
		return numMonths + " months";
	} else if (years == 1) {
		if (numMonths == 0) {
			return "1 year " + days + " " + (days == 1 ? "day" : "days");
		}

		if (useMonths) {
			return "1 year " + numMonths + " " + (numMonths == 1 ? "month" : "months");
		}

		return "1 year " + days + " " + (days == 1 ? "day" : "days");
	}

	return years + " years";
}

document.addEventListener("DOMContentLoaded", function() {
    var timestampElements = document.querySelectorAll("[data-timestamp]");
    var pairsList = [];

    [].forEach.call(timestampElements, function(timestampEl) {
        var timestampElType = timestampEl.getAttribute("data-timestamp-type");
        if (timestampElType != "timedelta");
        var milliseconds = parseInt(timestampEl.getAttribute("data-timestamp")) * 1000;
        pairsList.push([timestampEl, timestampElType, milliseconds])
    })

    function performTimestampUpdate() {
        pairsList.forEach(function(pair) {
            var timestampEl = pair[0];
            var type = pair[1];
            var milliseconds = pair[2];

            var timedelta = Date.now() - milliseconds;
            var formattedDelta = formatTimedeltaShort(timedelta);
            // console.log(timestampEl.textContent, formattedDelta);

            if (formattedDelta != "now") formattedDelta += " ago";
            timestampEl.textContent = formattedDelta;
        });
    }

    performTimestampUpdate();
    setInterval(performTimestampUpdate, 1000 * 30)
})