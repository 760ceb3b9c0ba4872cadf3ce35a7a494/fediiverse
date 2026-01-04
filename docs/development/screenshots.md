# OLV screenshot technical details
technical description of how screenshots (called "capture images") work in the Miiverse applet.  
thanks to [Enderspearl184](https://github.com/Enderspearl184) for making this possible :3

## Checking if a capture can be taken
To check if capturing is enabled, call
```js
cave.capture_isEnabled()
```
which will return a boolean. You can also check for a specific screen using
```js
cave.capture_isEnabledEx(screen)
```
(see below for valid options for `screen`)

Bafflingly, you are allowed to completely ignore whether the capture is enabled, and all of the following steps will still work
if it is disabled. But if no capture data exists, then garbage data will be read (presumably uninitialized memory) and you'll get a garbled screenshot.  

As an alternative to `cave.capture_isEnabled()`, which might return `false` even when a capture is available, you can call
```js
cave.sap_exists()
```
to see if any software is suspended. It seems that if software is suspended a capture will always be successful, even if capture is "disabled".

## Assigning capture images to keys
Call the function    
```js
cave.lls_setCaptureImage(key, screen)
```  
where `key` is a string key to use, and `screen` is one of the following:
- 0: bottom screen
- 1: top screen left eye
- 2: top screen right eye
- 3: top screen? (not always present?)

## Displaying the capture image in an `img` tag
Call 
```js
cave.lls_getPath(key)
```
to get a path in the form of `http://lls/{key}`, 
then set the `src` tag of an `img` to this path:
```js
img.setAttribute("src", cave.lls_getPath(key));
```

## Sending the capture image in a form
Add an `<input type="file">` element to your form, then set its `lls` attribute to the key:
```js
input.setAttribute("lls", key);
```
The input element must then be clicked to properly attach the file.  
To avoid requiring the user to do this manually, you can click it from JS:
```js
input.focus();
input.click();
input.blur();
```
(it must be focused before clicking)  

The input element can be hidden in CSS. If not hidden, it will render as a nonfunctional "choose file" button.
The capture is submitted as a JPEG.

## Doing other things with the capture image
It doesn't seem like much else can be done with the capture image.  

The capture image is kind of a "ghost member" of lls.  
The key specified will appear like other keys do in the count returned by `cave.lls_getCount()` and returned by `cave.lls_getKeyAt(n)`, but
nothing is returned when calling `cave.lls_getItem(key)`.

Attempts to fetch the capture path with `XMLHttpRequest` or to load the capture image in a `canvas` element were also not successful.

## Example
(you can view the complete fediiverse implementation in `addScreenshotToForm()` from [new.js](/fediiverse/servers/olv/static/scripts/new.js))

Assuming there is already a form in your HTML, this code will add a screenshot of the top screen to the form:
```js
cave.lls_setCaptureImage("capture_top", 1);  // top screen, left eye

var form = document.querySelector("form");
var inputEl = document.createElement("input");
inputEl.setAttribute("name", "top-screenshot");
inputEl.setAttribute("type", "file");
inputEl.setAttribute("lls", "capture_top");  // same key from before
inputEl.focus();
inputEl.click();
inputEl.blur();
inputEl.style.display = "none";  // hide it
```

The form can then be submitted as normal, and the `top-screenshot` field in the formdata will contain a 400x240 JPEG screenshot of the top screen.
