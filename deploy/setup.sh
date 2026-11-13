#!/usr/bin/env bash
# Paytience web server setup for a fresh Ubuntu 22.04 / 24.04 cloud server (docs/DEPLOY.md).
# Run from the repository folder:  sudo bash deploy/setup.sh
# Safe to run again: it keeps an existing .env, keys, database and certificates.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=(docker compose -f docker-compose.prod.yml)
CADDY_IMAGE=caddy:2.8.4-alpine

say() { printf '\n\033[1;33m== %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }
env_get() { grep -E "^$1=" .env 2>/dev/null | tail -1 | cut -d= -f2- | sed -e "s/^'//" -e "s/'$//"; }
env_set() {  # single quotes: a bcrypt hash contains '$', which Docker Compose would otherwise expand
  local k=$1 v=$2
  touch .env && chmod 600 .env
  grep -vE "^$k=" .env > .env.tmp || true
  printf "%s='%s'\n" "$k" "$v" >> .env.tmp && mv .env.tmp .env && chmod 600 .env
}

[ "$(id -u)" -eq 0 ] || die "run with sudo: sudo bash deploy/setup.sh"
[ -f docker-compose.prod.yml ] || die "run this from the Paytience repository folder"

say "1/6 Docker"
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  apt-get update -q
  apt-get install -y -q docker.io docker-compose-v2
  systemctl enable --now docker
fi
docker compose version

say "2/6 Firewall: only SSH, HTTP and HTTPS are open"
if command -v ufw >/dev/null 2>&1; then
  ssh_port=$(echo "${SSH_CONNECTION:-x x x 22}" | awk '{print $4}')
  ufw allow "${ssh_port}/tcp" >/dev/null   # the port you are connected on right now: never lock yourself out
  ufw allow OpenSSH >/dev/null
  ufw allow 80/tcp >/dev/null && ufw allow 443/tcp >/dev/null && ufw allow 443/udp >/dev/null
  ufw --force enable >/dev/null && ufw status | sed -n '1,12p'
else
  echo "ufw not installed: open only ports 22, 80 and 443 in your cloud provider's firewall."
fi

say "3/6 Settings (.env, readable only by root)"
if [ -z "$(env_get PAYTIENCE_DOMAIN)" ]; then
  read -rp "Domain for Paytience (e.g. app.example.com, its DNS A record must point to this server): " d
  d=${d#https://}; d=${d#http://}; d=${d%%/*}
  [[ "$d" =~ ^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ || "$d" == localhost ]] || die "not a domain name: $d"
  env_set PAYTIENCE_DOMAIN "$d"
fi
if [ -z "$(env_get PAYTIENCE_PLAN)" ]; then
  echo "Lucid plans:"; ls config/rules/ | sed -n 's/\.yaml$//p' | sed 's/^/  /'
  read -rp "Plan [lucid_flex_25k]: " p; p=${p:-lucid_flex_25k}
  [ -f "config/rules/$p.yaml" ] || die "no plan file config/rules/$p.yaml"
  env_set PAYTIENCE_PLAN "$p"
fi
if [ -z "$(env_get PAYTIENCE_EDGE_HASH)" ]; then
  echo "Edge login = the first login wall (browser pop-up) in front of the whole site, except the TradingView webhook."
  read -rp "Edge login user name [paytience]: " u; u=${u:-paytience}
  read -rsp "Edge login password (12+ characters): " pw; echo
  [ ${#pw} -ge 12 ] || die "use at least 12 characters"
  read -rsp "Repeat it: " pw2; echo
  [ "$pw" = "$pw2" ] || die "passwords do not match"
  hash=$(printf '%s\n' "$pw" | docker run --rm -i "$CADDY_IMAGE" caddy hash-password | tail -1)
  unset pw pw2
  [[ "$hash" == \$2* ]] || die "could not hash the password"
  env_set PAYTIENCE_EDGE_USER "$u"
  env_set PAYTIENCE_EDGE_HASH "$hash"
fi

say "4/6 Build the app (first time: several minutes)"
if [ "${PAYTIENCE_SKIP_BUILD:-0}" = 1 ] && docker image inspect paytience-app >/dev/null 2>&1; then
  echo "PAYTIENCE_SKIP_BUILD=1: using the existing paytience-app image"
else
  "${COMPOSE[@]}" build
fi

if [ -z "$(env_get PAYTIENCE_MASTER_KEY)" ] || [ -z "$(env_get PAYTIENCE_WEBHOOK_SECRET)" ]; then
  keys=$("${COMPOSE[@]}" run --rm --no-deps -T api python -m app.cli keys)
  [ -n "$(env_get PAYTIENCE_MASTER_KEY)" ] || env_set PAYTIENCE_MASTER_KEY "$(echo "$keys" | sed -n 's/^PAYTIENCE_MASTER_KEY=//p')"
  [ -n "$(env_get PAYTIENCE_WEBHOOK_SECRET)" ] || env_set PAYTIENCE_WEBHOOK_SECRET "$(echo "$keys" | sed -n 's/^PAYTIENCE_WEBHOOK_SECRET=//p')"
  echo "New master key + webhook secret written to .env. Keep a copy of .env somewhere safe (password manager)."
fi

say "5/6 Dashboard login (second wall)"
"${COMPOSE[@]}" run --rm --no-deps api alembic upgrade head >/dev/null
admin=${PAYTIENCE_ADMIN_USER:-PayDay}
if "${COMPOSE[@]}" run --rm --no-deps -T api python -c "
import sys; from sqlalchemy import select
from app.db import make_engine, make_sessionmaker; from app.models import User; from app.settings import get_settings
s = make_sessionmaker(make_engine(get_settings().database_url))()
sys.exit(0 if s.execute(select(User)).first() else 1)" ; then
  echo "A dashboard user already exists (change its password: ${COMPOSE[*]} run --rm api python -m app.cli set-password $admin)"
elif [ -t 0 ]; then
  "${COMPOSE[@]}" run --rm --no-deps -it api python -m app.cli create-admin "$admin"
else  # no terminal (automation): the password comes from PAYTIENCE_ADMIN_PASSWORD and is never written anywhere
  [ -n "${PAYTIENCE_ADMIN_PASSWORD:-}" ] || die "no terminal: set PAYTIENCE_ADMIN_PASSWORD for this run"
  "${COMPOSE[@]}" run --rm --no-deps -T -e PAYTIENCE_ADMIN_PASSWORD api python -m app.cli create-admin "$admin"
fi

say "6/6 Start"
"${COMPOSE[@]}" up -d
for _ in $(seq 1 60); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' "$("${COMPOSE[@]}" ps -q api)" 2>/dev/null)" = healthy ] && break
  sleep 3
done
"${COMPOSE[@]}" ps

line="17 3 * * * root cd $(pwd) && bash deploy/backup.sh >> /var/log/paytience-backup.log 2>&1"
echo "$line" > /etc/cron.d/paytience-backup && chmod 644 /etc/cron.d/paytience-backup

domain=$(env_get PAYTIENCE_DOMAIN)
cat <<EOF

Paytience is running.
  Dashboard:  https://$domain   (edge login, then your Paytience login)
  TradingView webhook URL:  https://$domain/api/webhook/tradingview
  Webhook secret: the PAYTIENCE_WEBHOOK_SECRET line in .env (paste it into the alert message, never anywhere else)
  Daily database backup: 03:17 server time into ./backups (deploy/backup.sh)
If the browser shows a certificate error, the DNS A record for $domain does not point to this server yet:
fix it, wait a few minutes, then: ${COMPOSE[*]} restart caddy   (logs: ${COMPOSE[*]} logs caddy)
EOF
