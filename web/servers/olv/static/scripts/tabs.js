function initTabs() {
    try {

        var tabs = [
            "home",
            "trending",
            "local",
            "federated"
        ]
        var tabNames = {
            "home": "Home",
            "trending": "Explore",
            "local": "Local",
            "federated": "Federated"
        }
        var currentTab = document.documentElement.getAttribute("data-timeline-kind");
        var currentIndex = tabs.indexOf(currentTab);

        function confirmScrollDown() {
            var scrollTop = cave.brw_getScrollTopY();
            if (scrollTop > 360) {
                var dialogResult = cave.dialog_twoButton(
                    "", "Are you sure you want to switch timelines?",
                    " Cancel", " Switch"
                );
                if (dialogResult != 1) {
                    return false;
                }
            }
            return true;
        }

        addKeyEventListener("ZL", function() {
            if (currentIndex == 0) return;
            if (!confirmScrollDown()) return;

            var newTab = tabs[currentIndex-1];
            cave.dialog_beginWait("", "Switching to " + tabNames[newTab] + " timeline...");
            document.location = "/timeline?kind=" + newTab;
        });

        addKeyEventListener("ZR", function() {
            if (currentIndex >= (tabs.length - 1)) return;
            if (!confirmScrollDown()) return;

            var newTab = tabs[currentIndex+1];
            cave.dialog_beginWait("", "Switching to " + tabNames[newTab] + " timeline...");
            document.location = "/timeline?kind=" + newTab;
        });
    } catch (e) {
        alert(e)
    }
}