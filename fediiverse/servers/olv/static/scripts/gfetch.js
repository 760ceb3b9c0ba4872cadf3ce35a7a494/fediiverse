/* thin wrapper for polyfilled fetch() that adds status checking and headers */

window.gfetch = function(input, init) {
    init = init || {};
    init.headers = init.headers || {};
    init.headers["Token"] = cave.lls_getItem("token");

    var promise = fetch(input, init);

    return promise.then(function(response) {
        if (!response.ok) {
            cave.snd_playSe("SE_CTR_COMMON_ERROR");
            cave.error_callFreeErrorViewer(0, "Error " + response.status + " while fetching resource." + "\n\nIf you encounter a bug, please file an issue on the fediiverse GitHub, thx!!!");
            throw ("HTTP error " + response.status);
        };
        return response;
    });
}