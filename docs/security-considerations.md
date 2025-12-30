# security considerations (for users)
fediiverse has been designed with privacy in mind. However, there are two major things to note about fediiverse:
1) fediiverse is software someone hosts, not a single online service; your fediiverse *instance* is operated *by someone*,
   and you should ideally trust that someone, and
2) fediiverse is beta software that has not been formally vetted for security, and comes with no warranty.

For the security-conscious, the rest of this document serves to outline the security implications of fediiverse and its 
potential risk scenarios.

## Credential storage
fediiverse is designed to avoid storing any credentials on the server. in fact, fediiverse has been designed to store 
only the bare minimum amount of identifying data necessary for operation, that being a list of the Fediverse instances 
the server has contacted before. 

fediiverse stores Mastodon login credentials locally on the 3DS, encrypted with a key stored on the server. 
Whenever you use fediiverse, the encrypted credential is sent to the server, enabling fediiverse to act on your behalf 
with your Fediverse instance only as long as needed and only at your (3DS's) request.

However, **there's no way to 100% trust the server**. like with any online service, you have no idea whether a 
fediiverse instance is actually running any specific software, and there is always a possibility that a server has 
broken these security features.

Critically, your 3DS does not speak the language of Mastodon, Misskey, etc. and this requires fediiverse to act as a
translator, speaking Nintendo language to your console and Fediverse language to your instance. This translation
definitionally requires fediiverse to handle your Mastodon credentials.

**You should exercise trust when choosing which fediiverse server to use, as you would (i hope!!!) when giving any 
website or service access to your account.**

(To mitigate these risks, your Fediverse instance admins could host a fediiverse server just for your community, 
which would avoid the risk of a rogue server entirely. You can also host fediiverse for just yourself if you have the
technical knowledge.)

## Network connection security
due to limitations of the 3DS's built-in networking capabilities, fediiverse communicates using relatively weak 
encryption[^1] compared to modern standards.
The end-to-end security of your data over a Wi-Fi connection cannot be guaranteed, and a determined attacker may be able
to use this to gain access to your Mastodon account. The best way to mitigate this is to only
use fediiverse on Wi-Fi networks you trust.  

**If you are worried about the security of your Mastodon account against highly targeted attacks, do not use fediiverse.**

The fediiverse Setup Utility briefly uses an unencrypted connection for initial setup, but this does not occur during 
normal operation. This connection is only used to download necessary configuration data, and no credentials are sent.

[^1]: Technical details: fediiverse negotiates an [AES256-SHA](https://ciphersuite.info/cs/TLS_RSA_WITH_AES_256_CBC_SHA/) cipher over TLS v1 or v1.1, and each instance 
generates its own certificate chain for that instance's users only.

## Device security
The 3DS is not a secure device. When you are logged into fediiverse, anyone with physical access to 
your 3DS will have access to your Mastodon account (because that's the whole point of fediiverse!)  
  
You can always log out of fediiverse from its settings menu, or, from another device, revoke its access to your 
Fediverse account using your instance's account settings page.

