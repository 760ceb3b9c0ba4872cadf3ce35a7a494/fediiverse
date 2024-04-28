var _keyIdx = {
    "13": "A",
    "66": "B",
    "88": "X",
    "89": "Y",

    "76": "L",
    "82": "R",
    "87": "ZL",
    "90": "ZR",

    "38": "up",
    "40": "down",
    "37": "left",
    "39": "right"
}

var _keyDown = {}
var _keyCallbacks = {}

function isKeyDown(key) {
    return _keyDown[key] == true;
}

function forceAllKeysDown() {
    for (var keyCodeStr in _keyIdx) {
        _keyDown[_keyIdx[keyCodeStr]] = false;
    }
}

document.addEventListener("keydown", function(event) {
    var keyName = _keyIdx[event.keyCode.toString()]
    if (!keyName) return;
    _keyDown[keyName] = true;
    console.log(keyName, "pressed");

    if (_keyCallbacks[keyName]) {
        _keyCallbacks[keyName].forEach(function(callback) {
            callback();
        })
    }
});

document.addEventListener("keyup", function(event) {
    var keyName = _keyIdx[event.keyCode.toString()]
    if (!keyName) return;
    _keyDown[keyName] = false;

    console.log(keyName, "released");
});

function addKeyEventListener(keyName, callback) {
    if (!_keyCallbacks[keyName]) {
        _keyCallbacks[keyName] = [];
    }
    _keyCallbacks[keyName].push(callback)
}

forceAllKeysDown();  // inits it to all false