# setup pt 2: the 3ds client
## step 1: custom fw
your 3ds has to be modded for any of this to work. if yours isnt you can follow the instructions at https://3ds.hacks.guide/.

once youre done you should have GodMode9 and Luma3DS on your device.

## step 1.5: auth server
so as i was working on this, nintendo shut down the nintendo network online services that the 3ds needs for miiverse to work.
even if you replace the miiverse-specific servers miiverse points to, it wont do anything if NNID isnt working, which it doesnt anymore.

so as of now, you need to install a cfw that replaces this auth server. ive been using Pretendo for this purpose.

so follow the [pretendo install instructions](https://pretendo.network/docs/install/3ds). they have their own miiverse replacement server thing which we will overwrite later.
make sure you're properly logged in to a Pretendo account in the NNID settings on your device.

## step 2: export the miiverse applet
we need to hack the miiverse applet to point it at our custom servers. 
the first step is to extract the miiverse app from the 3ds.

shut down your 3ds, then power it on while holding the start button. this will bring you into "godmode9" which is some
kind of cfw multitool. handle any dialogs if they come up.

once you get to the file browser in the `[root]` section, select the `SYSNAND CTRNAND` item (on my system mounted as `1:`)
then navigate to this path:
`1:/title/00040030`

(00040030 means [System Applets](https://www.3dbrew.org/wiki/Title_list#00040030_-_System_Applets))

next you have to go to the folder for the specific region of your device:

| region | id         |
|-------:|:-----------|
|  japan | `0000BC02` |
|    usa | `0000BD02` |	
| europe | `0000BE02` |

mine is from the US so my folder is `1:/title/00040030/0000bd02`.

from there, go to the `/content` folder and select the `.app` file. then, under `NCCH iamge options...`, select `extract .code`.

it should say it extracted successfully! make sure it extracted to the sd card (`0:`) and if not there's some option somewhere to change that.
hold down R while pressing START and your device will shutdown!

next, get the exported file off your device. you can remove the SD card and put it in a computer, or you can boot your device up and use [ftpd](https://github.com/mtheall/ftpd) to transfer it wirelessly.
on my device it exported to `0:/gm9/out`, which means it'll be in the `/gm9/out` folder on the root of your SD card.

on my device the filename was `000400300000BD02.dec.code` but on yours itll match your region ofc.
copy that file to your computer. 
rename this file to `code.bin` and place it in the `/patch` directory in this repo.

once you're done with this, leave the SD card in the computer or keep the FTP server going. 
you won't need to use your device again until later.

## step 3: build the patch
first you need to install two dependencies: [flips](https://github.com/Alcaro/Flips) and [armips](https://github.com/Kingcom/armips). 
you might be able to find release builds somewhere, but i just built them myself and it was fine.

you also need `make` so im assuming you have the normal dev environment set up.

put those into your path (or if you're too lazy just copy them in the `/patch` directory).
next, cd into the `/patch` directory and run `make`.

if you did everything right you should see `code.ips` appear in `/patch/out`. yaaaaaay :3 :3 :3 :3 :3

## step 4: copy the cert & patch
first, copy the `/cert/ca_cert.pem` file from this repo to `/3ds/fediiverse.pem` on the device.  
next, copy the `code.ips` to the folder `/luma/titles/00040030________/` where the blank space is the applet ID from earlier.
for example, i copied my `code.ips` to `/luma/titles/000400300000BD02/code.ips`. 
if you installed pretendo earlier the folder and file will already exist; ignore and overwrite that.

now make sure the sd card is in the device and turn it off.

## step 5: boot the device with the patch
turn on the device while holding SELECT. it should come up with a "luma3ds configuration" screen. if it doesnt, shutdown and try again.

make sure "Enable loading external FIRMs and modules" and "Enable game patching" are both on, then press START to boot the device.

## step 6: internet settings configuration
open the Settings app and navigate to the Connection Settings. 
click on the Connection corresponding to your network and then click "Change Settings", then press the right arrow and
click "DNS". turn off "Auto-Obtain DNS" and then press "Detailed Setup", and type in your computer's local IP as the primary DNS.
you can leave the secondary DNS blank.

## step 6: yesssssss
open the miiverse applet and it should load!!

if you did all this lmk on discord @760ceb3b9c0ba4872cadf3ce35a7a494 or on mastodon @760ceb3b9c0ba4872cadf3ce35a7a4@wetdry.world