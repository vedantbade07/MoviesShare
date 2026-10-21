# Security

MovieShare is a **personal-use** tool, not a hardened production server.

## Please remember
- It uses plain HTTP. Use it only on `localhost`, a trusted home network, a private VPN (like Tailscale), or behind an HTTPS tunnel.
- **Never port-forward it directly to the internet.**
- Anyone with the username and password can see every file in the shared folder (symlinks are blocked).
- Use a long, unique password (12+ characters).

## Reporting a problem
Found a security bug? Please open a GitHub issue marked **security** without posting exploit details publicly, or contact the maintainer privately through their GitHub profile.
