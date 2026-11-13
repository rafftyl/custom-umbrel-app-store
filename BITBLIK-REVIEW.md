Requires UI/UX UAT approval from the maintainer

## Screens and flows to review

- Umbrel community store app detail: BitBlik Coordinator; preview warning,
  x64 requirement and Lightning dependency.
- Umbrel app tile and app-proxy launch on port 28766, path /.
- Upstream monitoring dashboard /, offers view and /ws/offers updates.

1. Install from the community store with Lightning Node already installed.
2. Open the app while disabled: no coordinator relay/wallet calls; dashboard
   may show missing-schema errors before first coordinator activation.
3. Confirm an unauthenticated browser cannot reach dashboard data/WebSockets
   through the gateway; confirm no direct backend host ports exist.
4. Follow README manual configuration and restricted macaroon provisioning.
5. Activate only after explicit approval; verify current LND TLS certificate,
   all nine allowed RPCs and refusal of unrelated wallet/admin RPCs.
6. Restart app and user manager/node; identity/database/secrets must persist.
7. Stop, take backup and verify data-preserving recovery on disposable hardware.
8. Independently authorize any live financial acceptance; do not infer it from
   this package's no-wallet smoke test.

States: installed-but-disabled, initial missing schema, loading, empty offers,
DB/relay/LND error, ready monitoring, WebSocket reconnect. Desktop/phone widths,
light/dark browser presentation. No kiosk or Archipelago UI is changed.
The dashboard is upstream UI, not a newly implemented setup/admin console.

## Evidence

2026-11-13, WSL Ubuntu disposable Docker, amd64:
- Four Python package tests pass: shell syntax, Compose render, security
  boundaries, secret preparation idempotence/missing-secret refusal.
- Real pinned images pulled; coordinator OCI revision checked against local
  upstream history. Published coordinator is 3311c2b, not local c8c16af.
- Internal-network smoke passes: PostgreSQL non-superuser app role/schema,
  disabled wrapper, coordinator startup without LND, dashboard HTTP and realtime
  trigger/listener startup, dashboard restart.
- No host app ports, wallet mounts, live LND, payments, public Nostr events,
  Git pushes or actual Umbrel installation were used.

## Open acceptance / publication gates

- Current-source coordinator image build and financial-safety review required
  before enabling production trading; upstream registry main is older than local
  source. Do not silently label this pin as the latest source.
- Real Umbrel community install, app-proxy authentication (including WebSockets),
  app restart/update/uninstall/reinstall and backup/restore not yet qualified.
- Real LND certificate SAN and restricted macaroon permission checks pending.
- Maintainer UI/UX UAT and review required. No approval or merge performed.
