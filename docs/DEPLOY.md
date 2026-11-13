# Paytience as a web server with your own domain

Result: `https://app.yourdomain.com` opens Paytience from any browser or phone, 24/7, with a real HTTPS certificate.
TradingView sends alerts to `https://app.yourdomain.com/api/webhook/tradingview`. Your PC can be off.

What runs on the server (`docker-compose.prod.yml`):

| Part | Job | Reachable from the internet? |
|---|---|---|
| Caddy | HTTPS certificate (Let's Encrypt, renewed automatically), edge login, forwards to the app | yes: ports 80 and 443 only |
| api | Paytience (dashboard, webhook, automation, watchdog) | no, only through Caddy |
| worker + Redis | background jobs | no |

Two login walls protect the dashboard: the **edge login** (browser pop-up, from Caddy) and then your **Paytience login**.
Only the TradingView webhook skips the edge login, because TradingView cannot log in. The app protects that path itself:
secret checked in constant time, stale and duplicate alerts refused, per-IP rate limit, size limit.

## What you need (you buy these; nothing is bought for you)

1. **A domain**, about $10–15 a year (Cloudflare Registrar, Namecheap, Porkbun …). Paytience uses a subdomain such as
   `app.yourdomain.com`.
2. **A cloud server**: Ubuntu 24.04, 2 vCPU, 4 GB RAM, 40 GB disk, about $6–12 a month (Hetzner, DigitalOcean, Vultr …).
   Pick a US East / Chicago region (closest to CME). Use SSH-key login.
3. **Ask Lucid first (VERIFY)**: is trading the accounts from a cloud server (VPS) allowed? Add it to the open Lucid
   questions (CrossTrade bridge, long evals). Do not hide it from Lucid.

## Setup (about 20 minutes)

1. At your domain provider add a DNS **A record**: name `app`, value = the server's IP address.
   On Cloudflare DNS set it to **DNS only** (grey cloud), so Caddy can get its certificate.
2. Log in to the server with SSH and get the code (private repo: use a GitHub token or a deploy key):
   ```
   git clone https://github.com/paysh-wrap/opogabuuga.git paytience && cd paytience
   git checkout ccr-49c22917-zlwvy3
   ```
3. Optional, to keep your current TradingView alerts unchanged: create `.env` with your current secret first
   (`PAYTIENCE_WEBHOOK_SECRET='…'`). Otherwise the script makes a new secret and you paste it into each alert.
4. Run the setup script and answer its questions (domain, Lucid plan, edge login, Paytience password):
   ```
   sudo bash deploy/setup.sh
   ```
   It installs Docker, opens only SSH/80/443 in the firewall, writes `.env` (readable only by root) with new keys,
   builds the app, creates your login, starts everything and installs a daily database backup.
5. Open `https://app.yourdomain.com` → edge login → Paytience login. Then on the Connections page add your keys again
   (they are stored encrypted with this server's master key).
6. In every TradingView alert set the webhook URL to `https://app.yourdomain.com/api/webhook/tradingview` and, if the
   secret is new, the secret in the alert message.

**Run only ONE Paytience at a time.** Before you arm accounts on the server, disarm them and turn automation OFF in the
desktop app (two copies on the same accounts could trade twice). Paytience still starts in PAPER mode; LIVE needs every
live gate (§1.5), exactly as on the PC.

## Daily use and upkeep

| Task | Command (in the `paytience` folder on the server) |
|---|---|
| Logs | `make server-logs` |
| Update to the latest code | flatten + disarm first, then `make server-update` |
| Backup now | `make server-backup` (daily at 03:17 automatically, newest 14 kept in `backups/`) |
| Stop / start | `make server-down` / `make server-up` |
| Change the Paytience password | `docker compose -f docker-compose.prod.yml run --rm api python -m app.cli set-password PayDay` |
| Change plan | edit `PAYTIENCE_PLAN` in `.env`, then `make server-up` |

Keep a copy of `.env` somewhere safe (password manager). Without `PAYTIENCE_MASTER_KEY` the stored keys cannot be read.
The desktop app's "Update available" button only works in the Windows app; the server updates with `make server-update`.

## Moving your history from the PC (optional)

Stop the PC app. Copy its `paytience.db` to the server, then:
`make server-down && docker compose -f docker-compose.prod.yml run --rm -v "$PWD/paytience.db:/import.db:ro" api cp /import.db /data/paytience.db && make server-up`.
Stored API keys only open with the same `PAYTIENCE_MASTER_KEY` as on the PC; otherwise add them again on the Connections page.

## Troubleshooting

- **Certificate error / site does not open**: the A record does not point to the server yet, or ports 80/443 are closed
  in the provider's firewall. Fix, wait a few minutes, `docker compose -f docker-compose.prod.yml restart caddy`, check
  `docker compose -f docker-compose.prod.yml logs caddy`.
- **TradingView alerts refused**: the Journal & Logs page shows the reason (`BAD_SECRET`, `STALE`, …).
- **Forgot the edge password**: delete the `PAYTIENCE_EDGE_HASH` line from `.env` and run `sudo bash deploy/setup.sh` again.
