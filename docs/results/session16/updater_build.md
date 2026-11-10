# Session 16 — Desktop auto-updater (D88)

## Create the GitHub token (one time, ~2 minutes)
1. github.com → your avatar → **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens** → **Generate new token**.
2. Name: `Paytience updates`. Expiration: your choice (e.g. 1 year; renew when it expires).
3. Resource owner: **paysh-wrap**. Repository access: **Only select repositories** → `paysh-wrap/opogabuuga`.
4. Permissions → Repository permissions → **Contents: Read-only**. Leave everything else at "No access".
5. **Generate token**, copy it (starts with `github_pat_`).
6. Paytience → **Connections** → "App updates (optional)" → **GitHub (app updates)** → paste → **Save & test**.
   It is stored encrypted and never shown again. Remove it any time; the app keeps working without it.

## How updating works
- On start (Windows desktop app) and with Settings → **Check for updates**, Paytience asks GitHub for the
  `desktop-latest` release and compares its commit with the one built into your copy (Settings → App version).
- If newer: a banner "Update available — Install now?". Nothing installs until you click **Install now**.
- Blocked (reason shown) while a position is open, an account is armed, or automation is not OFF.
- Download → size + sha256 check → unpack → Paytience closes → files swapped → new version starts. If the new
  version does not start within 2 minutes, the old one is restored and a banner says the update failed.
- Your data (`paytience-data`: keys, database, logs) is never touched. Log: `paytience-data/updates/update.log`.

## Tests
`backend/tests/integration/test_updater.py` (19 tests): version compare, token never returned/logged, no-token
path, install blocked when armed / position open, checksum + size mismatch abort, unsafe/corrupt zip, generated
.bat text, healthy-start cleanup, dry-run install. `make test` (869 passed, 5 skipped; frontend 71 passed),
`make lint`, `make typecheck` green. The .bat itself could not be run here (no Windows) — first real update on
Windows is the live test.
