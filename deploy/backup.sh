#!/usr/bin/env bash
# Paytience server backup: a consistent copy of the SQLite database (online backup API, safe while trading) into
# ./backups, keeping the newest 14. Run from the repository folder (setup.sh installs a daily cron job).
# Also keep a copy of .env elsewhere: without PAYTIENCE_MASTER_KEY the stored API keys cannot be decrypted.
set -euo pipefail
cd "$(dirname "$0")/.."
COMPOSE=(docker compose -f docker-compose.prod.yml)
stamp=$(date -u +%Y%m%d-%H%M%S)
mkdir -p backups && chmod 700 backups
"${COMPOSE[@]}" exec -T api python -c "
import sqlite3
src = sqlite3.connect('/data/paytience.db'); dst = sqlite3.connect('/data/backup.tmp')
with dst: src.backup(dst)
dst.close(); src.close()"
"${COMPOSE[@]}" cp api:/data/backup.tmp "backups/paytience-$stamp.db"
"${COMPOSE[@]}" exec -T api rm -f /data/backup.tmp
chmod 600 "backups/paytience-$stamp.db"
ls -1t backups/paytience-*.db | tail -n +15 | xargs -r rm -f
echo "$(date -u +%FT%TZ) backup ok: backups/paytience-$stamp.db"
