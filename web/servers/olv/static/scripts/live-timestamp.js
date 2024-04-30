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
			return Math.floor(delta.seconds) + "s"
        }

		if (delta.seconds < 3600) {
			minutes = Math.floor(delta.seconds / 60);
			return minutes + "m"
        }

		if (3600 < delta.seconds) {
			hours = Math.floor(delta.seconds / 3600);
			return hours + "h"
		}
	} else if (years == 0) {
		if (!useMonths) {
			return days + "d";
        }

		if (numMonths == 0) {
			return days + "d";
        }

		return numMonths + "m"
    } else if (years == 1) {
		if (numMonths == 0) {
			return "1y " + days + "d";
        }

		if (useMonths) {
			if (numMonths == 1) {
				return "1y 1m";
            }

			return "1y " + numMonths + "m";
        }

		return "1y " + days + "d";
    }

	return years + "y";
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

    setInterval(function() {
        pairsList.forEach(function(pair) {
            var timestampEl = pair[0];
            var type = pair[1];
            var milliseconds = pair[2];

            var timedelta = Date.now() - milliseconds;
            var formattedDelta = formatTimedeltaShort(timedelta);
            // console.log(timestampEl.textContent, formattedDelta);

            timestampEl.textContent = formattedDelta;
        })
    }, 1000 * 60)
})