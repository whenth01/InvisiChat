# Bnuy

*NOTE: This also might work on other providers/a local network, i've only gotten to testing it on tailscale*
***IMPORTANT NOTE: This guide may or may not work! Only the android path has been tested and confirmed to work***
## Setting up TailScale
1: Visit tailscale.com/download and get tailscale
2: Log in/sign up
3: Done.

## Setup

Tailscale admin console side panel > Settings > Keys > Auth keys

 Set the auth key to your needs, then copy the key Tailscale gives you once youve finished

Send your friend the authkey, then your friend has to ▼
(note, this is assuming they have tailscale installed too)

Android: 
Main menu of Tailscale app > Settings > Accounts > top right 3 dots > Use an auth key

MacOS:
```bash
/Applications/Tailscale.app/Contents/MacOS/Tailscale up --authkey=<the authkey you copied>
 ```
 
Linux:
```bash
tailscale up --authkey=<the authkey you copied>
```

Windows:
```bash
cd "C:\Program Files\Tailscale"
tailscale.exe up --authkey=<the authkey you copied>
```

Then send your friend your device's MagicDNS to begin chatting.
(Note: User devices invited by untagged auth keys will look identical to devices you add yourself, I recommend tagging authkeys when making them to seperate the two)