# hacks
fediiverse uses multiple hacks to get the app working properly in the Miiverse applet. here are a few of them.

## CSS `border-radius`
fediiverse has some weird `border-radius` styles in certain places. this is due to an apparent rendering error in the Miiverse applet
web engine where the top left border radius is smaller than the bottom right border radius even when a uniform radius is applied.
this has been compensated for in some places by adding multiple radii for each corner to counteract the effect.

## "token" query parameter
fediiverse passes the entire secret authentication token in the "token" query parameter whenever a page navigation occurs.
this is because fediiverse entirely circumvents the normal authentication system used by miiverse (which is designed for Nintendo Network IDs)
and instead uses a token stored in the applet's internal local storage. a consequence is that the applet won't send
the token on its own, so we have to send the state ourselves in JavaScript using query parameters. (it seems like cookies are not supported.)

fediiverse avoids keeping tokens and other query parameters in request logs with an nginx `log_format` rule.

## "405 Method Not Allowed" fix
on the methods that change state on posts (favouriting, reblogging, deleting, and bookmarking) fediiverse accepts both
GET and POST requests when it really should only accept POST. this is to fix a bug with the Miiverse browser on the 3DS
where after navigating backwards (for example with the B button) all subsequent requests made by JavaScript will ALWAYS
use the GET method even when POST is specified until another forwards navigation occurs. 

it's [bad practice](https://en.wikipedia.org/wiki/HTTP#Safe_methods) in HTTP for GET requests to modify data on the server.
due to the unique situation of fediiverse, the problems usually associated with this are probably
mitigated (like, the user can't accidentally navigate to these URLs, theres no history for them to appear in, nothing is cached or prefetched)

this may create issues if fediiverse is placed behind a cache/reverse proxy.

(code: look at the `@app.post` methods in [this file](/fediiverse/servers/olv/__init__.py))

## 34 character domain limit
you cannot create a fediiverse instance at a domain that is longer than 34 characters long.
additionally, fediiverse uses a short URL for discovery (`https://d.DOMAIN/v`) when other services use
longer subdomains (`setup.DOMAIN`, `img.DOMAIN`) and have readable paths unlike `/v`.

This is because fediiverse uses a binary patching technique to modify the Miiverse applet to override the service discovery URL.
The default server URL is `https://discovery.olv.nintendo.net/v1/endpoint` (46 bytes), so no
server URL can exceed 46 bytes in length. To get maximum possible space,
fediiverse uses a short subdomain (`d.`) and a short path (`/v`) taking up 12 bytes in total,
leaving 46-12=34 bytes free for the apex domain itself.
