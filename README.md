# ShockHub

A free, self-hosted multi-user PiShock remote. Create token links with custom limits and share them with anyone — no account needed for guests.

Built for VRChat with full OSC avatar integration via a local client app.

> ShockHub is completely free. No subscriptions, no paywalls.

---

## Download

Head to the [Releases](https://github.com/me0wg4ming/ShockHub/releases) page and download the latest `ShockHubClient-Setup.exe`, or download it directly:

**[⬇ Download ShockHubClient-Setup.exe](https://github.com/me0wg4ming/ShockHub/releases/download/v1/ShockHubClient-Setup.exe)**

> ✅ **0/70 on VirusTotal** – The installer is unsigned but clean.

> https://www.virustotal.com/gui/file/02bef12eb949214bb2d86f6e5a20758b5c9b99bf4b5ae7fe92bfaf734108e31d

**Windows (installer)**

Download and run `ShockHubClient-Setup.exe`. No Python installation required.

**Windows / Linux (from source)**

```bash
pip install -r requirements.txt
python client.py
```

A setup window appears on first launch. Enter your ShockHub username and password.

---

## What is ShockHub?

ShockHub lets you share your PiShock with friends and partners via simple token links. You set the limits — max intensity, max duration, number of uses, expiry time — and send the link. Guests just open it in any browser, no account needed.

The ShockHub Client runs locally on your PC and connects your avatar in VRChat via OSC, so your avatar reacts in real time when someone operates your shocker.

```
Guest (token link) ──► ShockHub Server ──► PiShock API
                              │
                        WebSocket (wss)
                              │
                       ShockHub Client
                       (your local PC)
                              │
                       VRChat OSC (port 9000)
```

---

## Features

- Each user has their own account, shockers and tokens — fully isolated
- Token links with configurable limits: max intensity, max duration, use count, expiry
- Single-user claim lock, activate-on-first-use timer
- Pause a shocker or revoke a token — changes reflect instantly on the token page
- PiShock credentials are validated against the API before being saved
- Local client sends OSC parameters to VRChat and shows Discord Rich Presence
- Auto-update: client updates itself silently on startup
- Password reset via email

---

## ShockHub Client

The client runs locally on your PC and bridges ShockHub with VRChat. It receives commands from the server over a secure WebSocket and forwards them to VRChat as OSC avatar parameters.

### OSC Parameters

| Parameter | Type | Description |
|---|---|---|
| `SHOCK/IsShocking` | Bool | True during shock, resets after |
| `SHOCK/IsVibrating` | Bool | True during vibrate (including warning), resets after |
| `SHOCK/IsBeeping` | Bool | True during beep, resets after |
| `SHOCK/Intensity` | Float | 0.0–1.0 relative to token max intensity |
| `SHOCK/Duration` | Float | 0.0–1.0 relative to token max duration |
| `SHOCK/SendSignal` | Bool | Pulses on every operate — useful as a shared animator trigger |
| `SHOCK/Collar` | Bool | Heartbeat sent every 5s while client is connected |

---

## Token System

Tokens are shareable links tied to a specific shocker.

| Setting | Description |
|---|---|
| Max Intensity | Hard cap enforced server-side (1–100%) |
| Max Duration | Hard cap enforced server-side (1–15s) |
| Use Limit | Token stops working after N uses. Empty = unlimited |
| Expires After | Token expires after N hours. Empty = never |
| Single User | Only the first browser to open the token can use it |
| Activate on First Use | Expiry timer starts on first use, not on creation |

---

## Changelog

### v1.00 (2026-05-02)
- Initial release

---

## License

© 2026 me0wg4ming. All rights reserved.

This project is source-available. You may view and study the code, but you may not copy, redistribute, or use it in your own projects without explicit written permission.

---

## Disclaimer

This tool is intended for consensual use between trusted parties. Always ensure the person running the client has given explicit consent. The developers are not responsible for misuse.
