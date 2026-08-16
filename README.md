# Bnuuy :3

*NOTE: This also might work on other providers/a local network, i've only gotten to testing it on tailscale*
## Installing TermChat
Linux (Debian, Ubuntu)
```bash
sudo apt update
sudo apt install python3 python3-pip mpv
``` 

Linux(Fedora)
```bash
sudo dnf update
sudo dnf install -y python3 python3-pip mpv
```

Linux (centOS)
```bash
sudo dnf install -y python3 python3-pip
```

Linux (Arch)
```bash
sudo pacman -Syu
sudo pacman -S python python-pip
```

Windows
```bash
winget install Python.Python.3.13
```

MacOS
```bash
brew install python3
```

Android(termux)
```bash
pkg upgrade
pkg install python
```

Then
```bash
pip install termchat
```
Or, if you want to see termchat's code
```bash
git clone https://github.com/whenth01/termchat.git
cd termchat
```
(Assuming you have git installed)

Current branches:
dev (the stuff im currently working on)
main (stable releases)


## Enabling chat
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