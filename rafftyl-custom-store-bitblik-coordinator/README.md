# BitBlik Coordinator for Umbrel â€” x86-64 preview

Runs the coordinator, PostgreSQL 16 and the upstream monitoring dashboard.
The only browser entry is Umbrel's authenticated app proxy, port **28766**.
No database, coordinator or dashboard backend port is published directly.
No domain or inbound public port is required; the coordinator uses Nostr relays.

## Status and image provenance

This is a local preview, not a published/approved release. Tested in disposable
Docker on x86-64; actual Umbrel UI, LND TLS/macaroon and payment acceptance remain
outstanding. Do not send production funds based solely on the smoke test.

Pinned registry images verified on 2026-11-13:
- coordinator 0.13.0: OCI source revision
  `3311c2b1c1f55ad0a8ed31e0c02506f2516153dd`.
  Digest `50d4b501a33d2898324f9729a3b23d5a968207077acfcb3e1bdb5520ea50c7c0`.
- dashboard: tag `sha-e6a379f`,
  digest `e0809c874cd9c875ed41b79d1861959b4aa9bd4546ebaf85e8e19a20f805d3d2`.
- PostgreSQL: 16-alpine,
  digest `f377d590e5474681d4d7838635031a2b50647923b7abfa803ce9b5ff35d5c663`.

The coordinator pin is the available published image, NOT the newer local
BitBlik checkout. In particular, local revision 7bb0061's coordinator-info fix
is not represented by this image. Updating the pin requires repeating tests.

## 1. Install through your community store

Once this branch has been reviewed and published to your store's main branch,
refresh the existing Rafftyl community store and install **BitBlik Coordinator**.
Umbrel will require Lightning Node. Start/unlock LND first.
Open the tile: the monitoring dashboard is behind Umbrel login. Trading is
**disabled**. Before activation, missing coordinator tables can produce dashboard
errors; this is not a successful trading readiness state.

## 2. Configure on the Umbrel host

SSH to Umbrel and run these commands. Default installation root:

	sudo -i
	APP=/home/umbrel/umbrel/app-data/rafftyl-custom-store-bitblik-coordinator
	test -f "$APP/umbrel-app.yml"
	nano "$APP/data/coordinator/settings.env"

Set NAME, amount limits, fees and relays. Configure a real published
TERMS_OF_USAGE_NADDR. This file is trusted shell configuration: quote names
containing spaces and never paste commands from untrusted sources.
Do not put wallet passwords, private keys or tokens in Git or screenshots.
No personal Nostr key is necessary; upstream creates a dedicated key on first
activation in data/coordinator/coordinator_private_key.hex.

## 3. Provision restricted LND access

This explicit operation calls LND bakemacaroon but makes NO payment. The token
permits GetInfo, invoice lookup/decode, hold invoice creation/subscription/
settlement/cancellation, Lightning payment sending and payment tracking.
It cannot open/close channels or send on-chain funds. It still has significant
spending authority: amount limits are app policy, NOT cryptographic wallet limits.
The app never mounts LND's admin macaroon, wallet database or Docker socket.

	bash "$APP/hooks/provision-lnd" mainnet

Use the actual Lightning network instead of mainnet if appropriate. Provisioning
refuses to overwrite an existing token. It finds the running LND container by
Compose labels, uses its own lncli and copies only the newly baked token.
No wallet unlock password is requested or stored. LND must already be unlocked.

## 4. Explicitly enable trading

Only do this after reviewing terms, fees, liquidity and the spending authority:

	install -o 1000 -g 1000 -m 600 /dev/null "$APP/data/coordinator/ENABLED"

Then restart **BitBlik Coordinator only** using Umbrel's app menu. Do not restart
LND or Bitcoin. Open the dashboard and verify coordinator startup, database and
relay connectivity. Inspect app logs locally if needed; never publish key files.
Use the coordinator's public key in BitBlik to identify your coordinator.
Do not send a test payment until you separately decide to authorize it.

## Routing fee ceiling (0.13.0-umbrel.2 and later)

The coordinator routing budget is separate from `TAKER_FEE`. To override the
budget, edit the existing `data/coordinator/settings.env` on Umbrel and add:

```sh
TAKER_ROUTING_FEE_LIMIT_PERCENT=0.30
```

Check the shell syntax with `sh -n settings.env` from that directory and
restart **BitBlik Coordinator only** from Umbrel. `0.30` means 0.30% of the
net taker payout, rounded up to whole sats, with a 10-sat floor. Accepted
values are 0.01 through 100 with at most two decimal places. An unset or blank
setting keeps the old ceiling: 20% of the taker fee, rounded up, minimum 10
sats. This budget does not change the taker's fee or net payout.

Previously saved attempts keep their original routing budget. Never retry a
pending, unknown, or already paid attempt. A definitively failed and unpaid
BOLT11 payout can use the new limit when the taker submits a fresh invoice for
the exact net payout on the existing offer. Do not delete or edit payment rows.

## 5. Disable and recovery

Removing ENABLED only takes effect on the next coordinator restart; it does not
stop an already running worker. Stop the app through Umbrel first, then:

	rm -f "$APP/data/coordinator/ENABLED"

Restart leaves the coordinator idle. Pausing with in-flight trades can prevent
timely settlement: drain/reconcile first whenever possible. Preserve the original
wallet and all payment records. A timeout or unknown payment is NOT permission
to send another payment. Never run two coordinator copies against this database.

To revoke the credential, read data/coordinator/macaroon-root-key-id and use
LND's lncli deletemacaroonid for that exact ID (inside the same LND container).
This revokes ALL macaroons using that root ID. Do not delete arbitrary IDs.

## Backup and updates

Stop the app before filesystem backups; copy the entire app data directory,
including PostgreSQL, secrets, settings and coordinator identity, as one consistent
set. Also retain LND's own independent recovery/backups. A coordinator backup
is not a Lightning wallet backup. Browser Neko backups are separate too.

Do not uninstall or erase data to resolve a pending payment. Restore the matching
coordinator identity/database/secrets together; do not restore an old financial
snapshot and allow automatic execution without reconciling against the wallet.
Application upgrades may migrate database schema. Take a stopped backup first;
old binaries may not safely read a migrated DB. No downgrade promise is made.

The dashboard has its own DB-owning app role (not PostgreSQL superuser); upstream
creates realtime notification functions/triggers. It is a monitoring dashboard,
not a read-only SQL credential, setup wizard or dispute adjudication console.
Keep Umbrel app-proxy authentication enabled and do not publish its backend.

## Tests

From the store repository in Linux, with Python 3, PyYAML, Bash and Docker Compose:

	python3 tests/test_bitblik_package.py
	python3 tests/smoke_bitblik.py

The smoke test uses uniquely named containers, an internal Docker network and
synthetic database credentials. No LND, real keys, published Nostr events or
payments are involved. Run as a disposable test user with permission to chown
fixture directories to UID 1000 (the local test used root in WSL).
