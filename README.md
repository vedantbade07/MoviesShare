# 🎬 MovieShare

**Share a folder of movies from your own Windows PC and watch it in any web browser. Password protected. No installs beyond Python.**

Think of it as a tiny, private Netflix-style file browser for *your* files.

---

## ✨ What it does

| Feature | Details |
|---|---|
| 📁 Browse folders | Clean dark web page with folders and files |
| ▶️ Watch in browser | Plays video/audio your browser supports (MP4, WebM, and often MKV) |
| ⏩ Seek / skip ahead | Supports "byte ranges", so you can jump around in a video |
| ⬇ Download | Every file has a download button |
| 🔐 Password | Username + password required (Basic Authentication) |
| 🛡 Safe paths | Blocks `../` tricks and symbolic links so nobody can escape the shared folder |
| 📦 Zero dependencies | Only Python's built-in libraries. No `pip install` |

---

## 🧰 What you need

- A **Windows** PC (the code also runs on macOS/Linux with a different folder path)
- **Python 3.9 or newer** – download from <https://www.python.org/downloads/> and tick **"Add Python to PATH"** during install
- A folder with your files, for example `D:\Movies`

Check Python is installed by opening PowerShell and typing:

```powershell
python --version
```

---

## 🚀 Quick start (5 minutes)

### 1. Download the project
Click the green **Code** button on GitHub → **Download ZIP**, then extract it (for example to `D:\MovieShare`).
Or, with Git:

```powershell
git clone https://github.com/<your-username>/MovieShare.git
cd MovieShare
```

### 2. Start it
Open PowerShell inside the folder and run:

```powershell
python .\server.py --directory "D:\Movies"
```

You will see something like:

```
MovieShare is running.
Folder:   D:\Movies
Local URL: http://127.0.0.1:6789
Username: viewer
Password: a1B2c3D4e5F6g7H8
```

### 3. Open it
Go to **<http://127.0.0.1:6789>** in your browser and log in with the username and password shown. 🎉

> 💡 The password is randomly generated each time you start. Keep that window open. Press **Ctrl + C** to stop.

### Even easier: the launcher script

```powershell
.\Start-MovieShare.ps1
.\Start-MovieShare.ps1 -Folder "E:\Videos" -Port 8080
.\Start-MovieShare.ps1 -AllowNetwork      # allow other devices
```

If PowerShell says scripts are disabled, run this once for the current window only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

---

## 🌍 Watching from other devices

Pick **one** of these, from safest to least safe.

### Option A – Only on this PC (default, safest)
Nothing to do. It only listens on `127.0.0.1`.

### Option B – From anywhere with Tailscale (recommended)
[Tailscale](https://tailscale.com/) creates a private network between your devices.

1. Install Tailscale on your PC **and** on your phone/laptop. Sign in to the same account.
2. Start MovieShare so it accepts network connections:
   ```powershell
   python .\server.py --directory "D:\Movies" --host 0.0.0.0
   ```
3. Find your PC's Tailscale address (looks like `100.x.y.z`):
   ```powershell
   tailscale ip -4
   ```
4. On the other device open `http://100.x.y.z:6789` and log in.

If Windows Firewall blocks it, add an **inbound rule for TCP port 6789** limited to the **Private** profile (avoid the Public profile).

### Option C – Same Wi-Fi / home network
Use `--host 0.0.0.0`, then open `http://<your-PC-local-IP>:6789` from another device. Only do this on a network you trust.

### Option D – Temporary public link with Cloudflare Quick Tunnel
Gives an HTTPS link that anyone with the link **and** password can use. Good for a quick share, not for long-term use.

```powershell
# Terminal 1
python .\server.py --directory "D:\Movies" --host 127.0.0.1 --port 6789

# Terminal 2
cloudflared tunnel --url http://localhost:6789
```

Open the `https://...trycloudflare.com` address it prints.

---

## 🔑 Choosing your own username and password

Best way (keeps the password out of your command history):

```powershell
$env:MOVIESHARE_USER = "myviewer"
$env:MOVIESHARE_PASSWORD = "Use-A-Long-Unique-Password-Here"
python .\server.py --directory "D:\Movies"
```

The password must be **at least 12 characters**.

---

## ⚙️ All options

| Option | Default | Meaning |
|---|---|---|
| `--directory` | `D:\Movies` | Folder to share |
| `--host` | `127.0.0.1` | `127.0.0.1` = this PC only, `0.0.0.0` = other devices too |
| `--port` | `6789` | Port number |
| `--user` | `viewer` (or `MOVIESHARE_USER`) | Login name |
| `--password` | random (or `MOVIESHARE_PASSWORD`) | Login password, 12+ characters |

---

## ❓ Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick **Add Python to PATH**, then reopen PowerShell |
| `Shared folder does not exist` | Check the `--directory` path and wrap it in quotes |
| Video shows but no sound or won't play | The browser may not support that format/codec (common with some MKV files). Use **Download** and play it in VLC |
| Other device can't connect | Use `--host 0.0.0.0`, check Windows Firewall, and confirm both devices are on the same Tailscale/LAN |
| Port already in use | Choose another one, for example `--port 8080` |
| Forgot the password | Stop the server (Ctrl + C) and start it again to get a new one |

---

## 🛡 Security notes (please read)

- This is a **personal project**, not a hardened production server.
- It uses plain **HTTP**. Use it on localhost, a trusted network, a VPN like Tailscale, or behind an HTTPS tunnel.
- **Do not port-forward it to the public internet.**
- Anyone with the login can access **every file** in the shared folder, so share only a folder meant for this.
- Only share files you have the right to share.

See [SECURITY.md](SECURITY.md) for more.

---

## 🗂 Project layout

```
MovieShare/
├── server.py             # the whole web server (Python, standard library only)
├── Start-MovieShare.ps1  # optional Windows launcher
├── README.md             # this guide
├── SECURITY.md           # safety notes
├── CONTRIBUTING.md       # how to help
├── LICENSE               # MIT license
└── .gitignore
```

## 🤝 Contributing

Ideas and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

[MIT](LICENSE) – free to use, change, and share.
