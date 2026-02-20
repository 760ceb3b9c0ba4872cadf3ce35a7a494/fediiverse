var visibilityLabels = {
    public: "Public",
    unlisted: "Quiet public",
    private: "Followers",
    direct: "Mentioned"
};

var visibilityLabelsShort = {
    public: "Public",
    unlisted: "Quiet",
    private: "Followers",
    direct: "Mentioned"
};

function promptSelect(choices, currentChoice) {
    return new Promise(function(resolve, reject) {
        // lol this is a massive hack. read thru and ull see how funny this shit is
        // choices should be a list like this:
        /*
        [
            ["value", "Label"],
            ["value2", "Label2"]
        ]
        */
        // resolves with (value: string | null) => void, value is null if cancelled

        choices = choices.filter(function(choice) {
            return !!choice;
        });

        var scrollY = cave.brw_getScrollTopY();
        var targetPos = scrollY + 400;

        var selectEl = document.createElement("select");
        selectEl.style.position = "absolute";
        selectEl.style["-webkit-appearance"] = "none";
        selectEl.style.top = targetPos + "px";
        selectEl.style.left = "0px";
        selectEl.style.width = "1px";
        selectEl.style.height = "1px";
        // selectEl.style.display = "none";
        selectEl.style.opacity = "0";


        var totalIndex = 0;
        var choiceValues = {};

        function addSubChoices(parentEl, subChoices) {
            for (var index = 0; index < subChoices.length; index++) {
                var choice = subChoices[index];

                if (choice[1].constructor == Array) {
                    var optgroupEl = document.createElement("optgroup");
                    optgroupEl.setAttribute("label", choice[0]);
                    totalIndex++;
                    addSubChoices(optgroupEl, choice[1]);
                    parentEl.appendChild(optgroupEl);
                } else {
                    var optionEl = document.createElement("option");
                    optionEl.setAttribute("value", choice[0]);
                    optionEl.innerText = choice[1];
                    choiceValues[totalIndex] = choice[0];
                    if (typeof choice[2] == "boolean") {
                    	optionEl.disabled = !choice[2];
                    }
                    if (choice[0] == currentChoice) optionEl.selected = "selected";
                    parentEl.appendChild(optionEl);
                    totalIndex++;
                }
            }
        }
        addSubChoices(selectEl, choices);


        document.body.appendChild(selectEl);

        // will refocus this later:
        var rnActiveElement = document.activeElement;
        cave.select_setClosingCallback(function(index) {
            cave.select_resetClosingCallback();
            selectEl.parentNode.removeChild(selectEl);
            if (rnActiveElement) {
                rnActiveElement.focus();
            }

            if (index == -1) {
                resolve(null);
            } else {
                resolve(choiceValues[index]);
            }
        });

        // opening the choice will block keyup events, so we assume all buttons are immediately released when the dialog starts.
        forceAllKeysDown();

        cave.sendMouseClick(0, targetPos);
    });
}