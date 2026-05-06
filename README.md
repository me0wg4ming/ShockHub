# ShockGate

A free, self-hosted multi-user PiShock remote. Create token links with custom limits and share them with anyone — no account needed for guests.

Built for VRChat with full OSC avatar integration via a local client app.

> ShockGate is completely free. No subscriptions, no paywalls.

---

## Download

Head to the [Releases](../../releases) page and download the latest `ShockGateClient-Setup.exe`.

> ✅ **0/70 on VirusTotal** – The installer is unsigned but clean.

> https://www.virustotal.com/gui/file/c93b6b47789a111f7c2814001e807be344b314a34d92fe7e7c5d6b8c7b938a0c

**Windows (installer)**

Download and run `ShockGateClient-Setup.exe`. No Python installation required.

**Windows / Linux (from source)**

```bash
pip install -r requirements.txt
python client.py
```

A setup window appears on first launch. Enter your ShockGate username and password.

---

## What is ShockGate?

ShockGate lets you share your PiShock with friends and partners via simple token links. You set the limits — max intensity, max duration, number of uses, expiry time — and send the link. Guests just open it in any browser, no account needed.

The ShockGate Client runs locally on your PC and connects your avatar in VRChat via OSC, so your avatar reacts in real time when someone operates your shocker.

```
Guest (token link) ──► ShockGate Server ──► PiShock Broker (wss)
                              │
                        WebSocket (wss)
                              │
                       ShockGate Client
                       (your local PC)
                              │
                       VRChat OSC (port 9000)
```

---

## Features

- Each user has their own account, shockers and tokens — fully isolated
- Token links with configurable limits: max intensity, max duration, use count, expiry
- Single-user claim lock, activate-on-first-use timer
- Token pause/unpause — instantly block a token without deleting it
- Multi-shocker tokens — one token can control multiple shockers simultaneously
- Pause a shocker or revoke a token — changes reflect instantly on the token page via SSE
- No share codes needed — ShockGate connects directly via the PiShock Broker WebSocket
- Email verification required on registration
- Password reset via email
- Local client sends OSC parameters to VRChat and shows Discord Rich Presence
- Auto-update: client silently updates itself on startup via SHA256 hash comparison
- Rate limiting on login, register and password reset endpoints
- IP ban system (exact, CIDR, wildcard) managed from the admin panel
- Login history: last 5 IPs tracked per user
- Per-token activity logs, persistent across server restarts
- Admin SSE: admin panel receives live updates without polling
- Security headers: CSP, HSTS, X-Frame-Options, Referrer-Policy

---

## ShockGate Client

The client runs locally on your PC and bridges ShockGate with VRChat. It receives commands from the server over a secure WebSocket and forwards them to VRChat as OSC avatar parameters.

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

Tokens are shareable links tied to one or more shockers.

| Setting | Description |
|---|---|
| Max Intensity | Hard cap enforced server-side (1–100%) |
| Max Duration | Hard cap enforced server-side (1–15s) |
| Use Limit | Token stops working after N uses. Empty = unlimited |
| Expires After | Token expires after N hours. Empty = never |
| Single User | Only the first browser to open the token can use it |
| Activate on First Use | Expiry timer starts on first use, not on creation |
| Pause | Instantly block a token without deleting it |

---

## Changelog

### v1.04 (2026-05-06)
- No share codes needed — ShockGate now connects directly via the PiShock Broker
- Multi-shocker tokens: one token can now control multiple shockers at the same time
- Token pause/unpause: pause a token instantly without deleting it
- Email verification required on registration — unverified accounts are deleted after 24 hours
- Shocker uniqueness: a shocker can only be registered on one ShockGate account at a time

### v1.03 (2026-05-04)

**VRChat / OSC Detection**
- Client now detects whether VRChat is running and whether OSC is enabled, using VRChat's OSCQuery HTTP endpoint
- Three distinct states shown in the GUI: `Connected` (green), `Running – OSC disabled` (orange), `Not running` (red)
- VRChat status checked immediately on server connect and then every 5 seconds
- Heartbeat (`SHOCK/Collar`) only sent when VRChat OSC is actually reachable

**Collar Signal**
- `SHOCK/Collar = False` now sent to VRChat when the client exits cleanly
- `SHOCK/Collar = True` sent immediately on successful server authentication

**GUI**
- VRChat status row added to info block with colour-coded dot indicator
- System log increased in height and wraps long lines

**Email (server)**
- Registration and password reset emails now include a `text/plain` part alongside HTML, fixing SpamAssassin flags and improving deliverability

### v1.02 (2026-05-03)
- Adding a shocker no longer requires manually entering share codes — ShockGate fetches your shockers directly from PiShock
- Multiple shockers can be added in one step
- Token status badges on the dashboard: ACTIVE, EXPIRED, USED UP, NO SHOCKER
- Dashboard layout improvements

### v1.01 (2026-05-02)
- Client auto-updates itself on startup
- Discord Rich Presence added
- Token page updates shocker pause status in real time without page reload
- Invalid shockers are detected and flagged automatically
- FAQ section and safety disclaimer added to the landing page

### v1.00 (2026-05-02)
- Initial release

---

## License

© 2026 me0wg4ming. All rights reserved.

This project is source-available. You may view and study the code, but you may not copy, redistribute, or use it in your own projects without explicit written permission.

---

## Disclaimer

This tool is intended for consensual use between trusted parties. Always ensure the person running the client has given explicit consent. The developers are not responsible for misuse.
