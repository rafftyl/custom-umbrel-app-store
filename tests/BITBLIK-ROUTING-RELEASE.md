# Release BitBlik 0.13.0-umbrel.2

Do not merge the store branch before the public registry pin is verified. The
preparation commit intentionally keeps the currently published image and version.

## Review and publish the image

The coordinator source is BitBlik revision
`0ae85a4537bac75b7ff1ab01dfe74b1795160e79`, based on `3311c2b`.
The local branch is `rafftyl/taker-routing-fee-limit` in
`C:\Workspace\repos\Decentralized\Nostr\bitblik-routing-fee`. Publish the
reviewed branch to your BitBlik fork, not directly to upstream main. No node
files, secrets or wallet credentials belong in the source repo or image.

In PowerShell, on the build machine, publish the tested local image. Use a
short-lived [classic GitHub token](https://github.com/settings/tokens) with
`write:packages`. Paste it only at the Docker login password prompt. This uses
a temporary Docker client config; it is not needed on Umbrel.

```powershell
$cfg = (wsl -d Ubuntu -u root -- mktemp -d).Trim()
$local = 'bitblik-routing-local:0.13.0-umbrel.2'
$tag = 'ghcr.io/rafftyl/bitblik-coordinator:0.13.0-umbrel.2'
$expected = 'sha256:92f8dfd026e82348519e2ccd47d93943150f7bd3069de7c5739a36870eba05d5'
if ((wsl -d Ubuntu -u root -- docker image inspect $local --format '{{.Id}}').Trim() -ne $expected) { throw 'Wrong local image' }
try {
    wsl -d Ubuntu -u root -- docker --config $cfg login ghcr.io -u rafftyl
    if ($LASTEXITCODE -ne 0) { throw 'GHCR login failed' }
    wsl -d Ubuntu -u root -- docker tag $local $tag
    if ($LASTEXITCODE -ne 0) { throw 'Tag failed' }
    wsl -d Ubuntu -u root -- docker --config $cfg push $tag
    if ($LASTEXITCODE -ne 0) { throw 'Push failed' }
} finally {
    wsl -d Ubuntu -u root -- docker --config $cfg logout ghcr.io
    wsl -d Ubuntu -u root -- rm -r -- $cfg
}
```

Copy the **manifest digest printed by `docker push`**, not the local image ID.
On the `bitblik-coordinator` GitHub package page, open **Package settings** and
change visibility to **Public** so Umbrel can pull anonymously. Optionally link
it to your reviewed fork. Revoke the temporary token after the push.

## Pin and publish the Umbrel package

Run these from the Git-for-Windows store worktree at
`C:\Workspace\repos\Decentralized\Umbrel\custom-umbrel-app-store\worktrees\bitblik-routing-fee`,
using its corresponding WSL path for Docker and Python. Substitute the digest
from the push above; `$expected` is from the previous block.

```powershell
$digest = 'sha256:PASTE_THE_PUSH_DIGEST_HERE'
$store = '/mnt/c/Workspace/repos/Decentralized/Umbrel/custom-umbrel-app-store/worktrees/bitblik-routing-fee'
wsl -d Ubuntu -u root --cd $store -- python3 tests/pin_bitblik_routing_release.py $digest --expected-image-id $expected
```

The script pulls anonymously, checks image ID/platform/version/source label,
and only then changes the Compose pin, version and release notes. If it fails,
stop and do not release. Then run:

```powershell
wsl -d Ubuntu -u root --cd $store -- python3 tests/test_bitblik_package.py
wsl -d Ubuntu -u root --cd $store -- python3 tests/smoke_bitblik.py
```

From the store worktree, review the diff, commit the pin/version/README, push
`bitblik-routing-fee`, and open a PR to the store's `master`. Do not merge until
maintainer UI/UX UAT approval. For pre-merge UAT, use a separate disposable
Umbrel test environment/store; never run a second Drakkar worker with its
production key, database or wallet. The PR should start with the line below.

Requires UI/UX UAT approval from the maintainer

### Screens and flows to review

- Umbrel **Community App Store → BitBlik Coordinator**:
  `/community-app-store/:appStoreId/rafftyl-custom-store-bitblik-coordinator`.
  Install the previous preview in a disposable Umbrel environment, then check
  update visibility, loading state, failure handling and successful update to
  `0.13.0-umbrel.2`. Test desktop and phone widths, light and dark. No kiosk
  surface changes. Requires the store and Lightning Node dependency.
- Umbrel **BitBlik Coordinator dashboard** (`/` on the authenticated app proxy,
  port 28766). Reopen after update; verify loading, empty state and an existing
  history fixture if available, as well as unauthenticated denial. Desktop and
  phone, light and dark where available. Dashboard image and routes unchanged.
- BitBlik **Coordinator Console → affected offer → Payment details** (`/settings/coordinator-console`).
  With a test coordinator and test offer in `takerPaymentFailed`, verify the
  old saved cap and then the new cap on a fresh replacement invoice. Check
  loading, failed/unknown payment and successful retry in a synthetic or
  separately authorized test environment. No new app screen or settings widget.

## Update the live node only after approval

1. Check for any in-flight/unknown payments. Preserve all records and wallets.
   Schedule a short pause and use Umbrel's app menu to stop **BitBlik only**.
2. On Umbrel, take a private stopped backup of the app's `data` directory. The
   backup contains the key and wallet credential; do not copy it to a public
   location. Run once from a private SSH session:

   ```bash
   APP=/home/umbrel/umbrel/app-data/rafftyl-custom-store-bitblik-coordinator
   sudo sh -c 'umask 077; tar -C "$1" -czf "/root/bitblik-before-routing-$(date +%Y%m%d-%H%M%S).tar.gz" data' sh "$APP"
   sudoedit "$APP/data/coordinator/settings.env"
   sudo sh -n "$APP/data/coordinator/settings.env"
   ```

   Add `TAKER_ROUTING_FEE_LIMIT_PERCENT=0.30` once in the existing settings file.
3. Refresh/open the Rafftyl community store and select **Update** for the
   installed BitBlik Coordinator. Start it if the update leaves it stopped.
   Check the dashboard and the coordinator startup logs. Do not reinstall or
   restart Lightning Node. This release does not start a new payout for a failed
   invoice merely because the routing setting changed.
4. If the original 21,053-sat payout is definitively failed and unpaid and the
   424-sat test was separate, have the taker submit a fresh invoice on the same
   offer. That submission requests a real payout. Payment details should show
   38 sats for the old attempt and **64 sats** for the new one. If the result is
   pending/unknown, reconcile; do not send a second payment.
