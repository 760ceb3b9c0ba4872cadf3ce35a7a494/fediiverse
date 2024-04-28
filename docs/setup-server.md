# setup pt 1: the web server
## step 1: certificates
go to the /cert directory and run the `start_priv_key.py`, `start_ca_cert.py` and `start_leaf_cert.py` scripts in that order. 
if you want to additionally add a password to your certificates, i left options in the scripts that should work, but you probably don't need them.
you should now have all these files in your /cert folder: 
- `ca_cert.der`
- `ca_cert.pem`
- `ca_key.pem`
- `leaf_cert.der`
- `leaf_cert.pem`
- `leaf_key.pem`

## step 2: openssl
the 3ds has an ancient ssl stack that uses sslv3 for part of the bootstrapping process.
for ur server to support this old ass ssl youll need to build openssl with support for sslv3 and above.
i honestly don't know how to do it but i think you can follow these instructions: https://askubuntu.com/questions/893155/simple-way-of-enabling-sslv2-and-sslv3-in-openssl
if youre on a mac like me, i think you can download the files that homebrew uses to build openssl and just add the enable-sslv3 flags to those to make it easier. i think that's what i did but i forgot.

## step 3: nginx
so first you need to make sure your nginx is using the openssl you built. 
i think the one from homebrew on macos uses the openssl installed by brew by default, because it works on my machine™️, but idk how that really works. good luck

next you need to start nginx using the /nginx directory. my goto command is `killall nginx; nginx -p ./nginx -c nginx.conf` from the root of this repo. this will use port 443 on your machine.
(NOTE, the default logs path is `/var/log/nginx/3ds/`, so make sure that path exists or change it in the conf files!)

now hopefully its working. check the logs to make sure. 

to test if the old ssl support is working, you can use firefox. 
add the ca_cert.pem to your firefox certificate store, then enable the `about:config` flag that enables >=sslv3 (security.tls.version.min i think). 
then go to `https://127.0.0.1:443` and it should give you a Bad Gateway but the padlock should indicate your encryption is working.

## step 4: dns
make sure your computer is connected to the network your 3ds will be on. they should be on the same LAN and should be able to talk to eachother.
then find your computer's local IP on the network. edit your `/etc/hosts` file and add the following hosts, pointing to that local IP:

```
192.168.#.#	discovery.fediiverse.local
192.168.#.#	3ds.fediiverse.local
```
(replace that IP with your computer's IP)

now flush your dns cache if needed and make sure those hosts are resolving properly. `ping discovery.fediiverse.local` should reply from your computer's IP.

## step 5: dnsmasq
(idk how to do dns serving on Windows so good luck if you use that)

install dnsmasq and make sure it's running. im not amazing at networking so i dont totally understand all of what it does, 
but what it does here is it enables your computer to reply to dns queries and will respect your hosts file. this means you can
point another device's DNS to your local computer and try to resolve a url, and itll resolve to whatever you have set in your hosts file.

later youll point your 3ds DNS at your computer which will let it load those URLs.

## step 6: mastodon config
first, get the domain name ('hostname') of the mastodon instance you are on. set the `MASTODON_HOST` variable in the `.env` file to this.  
next, get the domain name of the server hosting the media of your mastodon instance. to do this, go to your timeline and find a post
that has an image, then right click and "copy image link", then get the domain name of that link. set the `MASTODON_MEDIA_HOST` env variable to that/

go to the "Development" section of the mastodon settings on your instance (`YOUR_INSTANCE/settings/applications`) and make a new application.
you can pick and choose the oauth scopes if you want, the service doesn't need all of them, but i give mine full r/w.

once you finish the app setup, copy the access token (next to "Your access token") and set the `MASTODON_TOKEN` env variable to that.

now your .env should loo something like this:
```
MASTODON_HOST=example.com
MASTODON_MEDIA_HOST=media.example.com
MASTODON_TOKEN=kbjkabkbfsjkbfskkbljj
```

## step 7: twemoji
download the twemoji repo (ideally this [newer non-twitter fork](https://github.com/jdecked/twemoji/)). 
find the `/assets/svg` path within the cloned repo and set the `TWEMOJI_ASSETS_PATH` variable in your .env to it.

now your .env should look like this:
```
MASTODON_HOST=example.com
MASTODON_MEDIA_HOST=media.example.com
MASTODON_TOKEN=kbjkabkbfsjkbfskkbljj
TWEMOJI_ASSETS_PATH=/path/to/twemoji-main/assets/svg
```

## step 8: servers
set up a python environment (probably 3.9+) with the dependencies from `requirements.txt`. then use uvicorn to start the two services,
`discovery` and `3ds`.

my commands for this are:
- `uvicorn web:servers.olv.app --port 19829 --host 0.0.0.0 --reload`
- `uvicorn web:servers.discovery.app --port 19828 --host 0.0.0.0 --reload`

the ports used there are used in the nginx config so if you want to change the ports you need to change it there as well.

also you should probably run the two commands in separate terminals.

## step 9: did you do it right though
ok so now you should be able to navigate to `localhost:19829/timelines?kind=home` in your browser. 
if that brings up the timeline, everything should be working.

to do a "full stack test" you can try using your computer (or another device with the DNS pointing to your computer's IP and the CA cert you made trusted)
and navigating to `https://3ds.fediiverse.local/timeline?kind=home`. that should bring up the same page as before.


<a href="./setup-client.md"><h3>the next step: setup the 3ds!! &#x3E;w&#x3C;</h3><a>
