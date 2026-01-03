# How to set up a fediiverse instance
This guide is intended for those with some server administration knowledge.

## Docker
As an alternative to setting fediiverse up manually, [KiyoNetcat](https://kiyo.ncat.cafe/) has created a [Docker configuration for fediiverse](https://git.craftingcomrades.net/KiyoNetcat/docker-fediiverse) which you may use instead of following these instructions!

## Prerequisites
You need:
- A domain name that you can create subdomains on.
  - **Your domain name must not exceed 34 characters in length.**[^1]
- A version of OpenSSL that supports TLSv1 and TLSv1.1. You may have to compile openssl manually for this, making sure the `enable-tls1` and `enable-tls1_1` flags are set.
- nginx, pointing to a version of OpenSSL that supports TLSv1 and TLSv1.1. If nginx is not pointing to the right OpenSSL
  version, you may have to recompile nginx with your new OpenSSL. You can check with `nginx -V`
- [git](https://git-scm.com) and [Python](https://python.org) installed (Python 3.9+ should work)
- A 3DS to test your server!

[^1]: See [34 character domain limit](../development/hacks.md#34-character-domain-limit) for more info.

## Downloading and installing requirements
1. Download the latest version of fediiverse from the 
   [GitHub releases page](https://github.com/760ceb3b9c0ba4872cadf3ce35a7a494/fediiverse/releases).
   Extract it, then enter the resulting directory in a command prompt.
2. Create a Python virtual environment in the fediiverse directory.
   - Unix:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     py -m venv .venv
     .venv\Scripts\activate
     ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Perform initial setup
1. Run the first time config tool to configure your instance. 
   - Unix:
     ```
     python3 first-time-config.py
     ```
   - Windows:
     ```
     py first-time-config.py
     ```
   The first time config tool will:
   - Set up paths for fediiverse to use
   - Download the Twemoji emoji set
   - Build an nginx config
   - Generate private keys and certificates
   - Write config information and secrets
2. Optional: for your own convenience, you may choose to set the `FEDIIVERSE_ROOT_PATH` environment variable
   to the path you specified.

## Running fediiverse
fediiverse is composed of multiple services that are mostly functionally independent and are
started separately. You are responsible for figuring out how to make these run automatically on startup,
which will vary based on operating system (for example, on Linux you would probably create systemd services.)

### Part 1: welcome, olv, img
These three services, `welcome`, `olv`, and `img`, are the dynamic parts of fediiverse.
`welcome` is what normal web browsers access to get started with fediiverse, and `olv` and `img` are
3DS-facing services that do all of the fediiverse-y work.  

You can start them with the following 3 commands:
- `uvicorn fediiverse.servers.welcome:app --port 19827 --log-level error`
- `uvicorn fediiverse.servers.olv:app --port 19829 --log-level error`
- `uvicorn fediiverse.servers.img:app --port 19830 --log-level error`

When running these commands, make sure the `FEDIIVERSE_ROOT_PATH` env variable is set to
the path you set up fediiverse in earlier.

#### Testing
- welcome: Navigate to `http://localhost:19827` in your browser and you should see the welcome page.
- olv: Navigate to `http://localhost:19829` in your browser and you should see "hello from fediiverse olv :3"
- img: Navigate to `http://localhost:19830` in your browser and you should see "hello from fediiverse img :3"

### Part 2: SSL and nginx
!!! there are some important gotchas here, so pay attention !!!

fediiverse comes with an nginx configuration that proxies and provides SSL for the `olv` and `img` services.
As a consequence of the unique SSL settings required by fediiverse, this nginx configuration **must be run alone or 
in front of** other HTTPS services you want to run on your server. This means that if you are running anything else on
port :443, you must instead bind that service to localhost on another port (say, 127.0.0.1:8443) and then use the 
"upstream" option in fediiverse to send all non-3DS requests to that server (in other words, putting fediiverse 
"in front" of your normal web server.) In this configuration, TLSv1.2 and TLSv1.3 traffic will be sent to your upstream
and TLSv1.1 and TLSv1 traffic will be handled by fediiverse. 

Even if you do not intend to host anything else on this system except for fediiverse, you still need to host the welcome
service somewhere, as fediiverse only provides SSL for 3DS-facing services and not those exposed to normal web browsers
(for which you need a real SSL certificate from a real certificate authority such as 
[Let's Encrypt](https://letsencrypt.org/).) So for any public facing fediiverse instance, you will need to use the
upstream setting.

If you omitted the upstream option during setup, you can edit it in `config.json` in your fediiverse root path and run
`build-nginx-configuration.py`. For example: `"proxy_upstream_https": "127.0.0.1:8443"`

To run the provided nginx config:
```
nginx -p $FEDIIVERSE_ROOT_PATH/nginx -c nginx.conf
```
with the `FEDIIVERSE_ROOT_PATH` environment variable set to your root path from earlier.

(You have to run this as a user with permission to bind to ports :80 and :443, such as root. 
Make sure to `killall nginx` between restarts.)

#### Example: exposing the welcome service

How you expose `welcome` is up to you, but you may choose to use nginx (alternatives include Caddy and HAProxy.)
If you already had a normal nginx/other proxy running on port 443, you may just add welcome to that!

An example nginx configuration that proxies HTTP port :19827 on HTTPS port :8443 would look something like this:
```nginx
server {
  listen 8443 ssl;
  server_name welcome.DOMAIN;

  location / {
    proxy_pass http://127.0.0.1:19827/;
  }
}
```
This would be part of a completely separate nginx instance than the fediiverse one.

Then, in fediiverse `config.json`, you would set `"proxy_upstream_https": "127.0.0.1:8443"` and run 
`build-nginx-configuration.py`. Now all TLSv1.2 and TLSv1.3 requests made to port :443 will be passed to port :8443,
which will then be passed to the welcome service on port :19827. TLSv1.1 and TLSv1.0 traffic will be sent to the various
fediiverse services. This configuration allows you to host both 3DS and normal traffic on the same host.

You can, of course, host any number of services on the upstream port with a proxy, but if none of them are
fediiverse's `welcome` then nobody will be able to log in!

#### Testing
Change directory into `FEDIIVERSE_ROOT_PATH`, then run this command to make sure TLS is working properly:
```
openssl s_client -host 127.0.0.1 -servername d.DOMAIN -port 443 -CAfile "./certificates/ca_cert.pem" -tls1_1 -cipher ALL@SECLEVEL=0
```
replacing `DOMAIN` with your domain name from earlier.

If the command does not fatally exit and you see `---`, you should be connected. 
(you can ignore messages like `unsuitable certificate purpose` and `invalid CA certificate`)

Try entering the following text, then press enter twice:
```
GET / HTTP/1.1
Host: d.DOMAIN
``` 
again replacing DOMAIN with your domain from earlier.  

If you get a response that includes "hello from fediiverse discovery", TLS and nginx should be working!

To test the upstream proxy, run the command again but change `-tls1_1` to `-tls1_2`, `-servername` to the domain of your
upstream service, and `-CAfile` to the CA file of the certificate you are using for that service. Or just try to request
to your website as normal with a web browser to ensure that it works as intended.

At this point, your fediiverse instance should be working!

## Further advice
- Go through the [configuration docs](./configuration.md) to further configure your instance.
- Join the [fediiverse Discord](https://discord.gg/UkvQGgDEPF) for help and updates.
- **Make sure that no query parameters ever appear in access logs**. 
  fediiverse uses query parameters for sensitive info including tokens. by default, fediiverse uses a custom nginx
  log rule to hide query parameters from request logs. make sure nothing else is logging entire URLs with query parameters.  
  See `combined_no_query` in [nginx.conf](../../fediiverse/nginx/_template/nginx.conf) 
  and [hacks.md#token-query-parameter](../development/hacks.md#token-query-parameter) for more info.
- you should configure a utility such as `logrotate` to delete logs automatically.
- you can configure uvicorn for better performance, especially if your instance is getting lots of requests. specifically,
  the `--workers` option allows you to spawn more than one process for improved concurrency.
  See the [uvicorn docs](https://uvicorn.dev/settings/) for more info.
- fediiverse services likely will not work from behind a reverse proxy service, 
  and you need to make sure any service you have in front of fediiverse, like a DDOS protection service, 
  is serving only the certificates generated by fediiverse, has legacy TLS support, and is otherwise okay with talking 
  to the 3DS. This is outdated software on an outdated device that does not play well with the modern web, and reverse
  proxy services are not designed with this in mind.
- Your fediiverse instance, by design, makes outbound requests to user-provided URLs (Fediverse instances). The server's 
  IP address will be exposed to these websites. You can restrict which instances the welcome service will accept
  in the [configuration](./configuration.md) and/or use a VPN for outbound traffic.
