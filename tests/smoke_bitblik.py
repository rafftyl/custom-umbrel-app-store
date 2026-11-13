"""Disposable internal-network smoke test. No internet, LND or payments."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

APP = Path(__file__).resolve().parents[1] / 'rafftyl-custom-store-bitblik-coordinator'
COORD = 'ghcr.io/bit-blik/coordinator@sha256:50d4b501a33d2898324f9729a3b23d5a968207077acfcb3e1bdb5520ea50c7c0'
DASH = 'ghcr.io/bit-blik/coordinator-dashboard@sha256:e0809c874cd9c875ed41b79d1861959b4aa9bd4546ebaf85e8e19a20f805d3d2'
PG = 'postgres:16-alpine@sha256:f377d590e5474681d4d7838635031a2b50647923b7abfa803ce9b5ff35d5c663'
name = 'bitblik-test-' + uuid.uuid4().hex[:10]
containers = []
def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, capture_output=True, text=True)
def run(suffix, image, args=(), env=None, volumes=None):
    full = name + '-' + suffix
    cmd = ['run', '-d', '--name', full, '--network', name, '--network-alias', suffix,
           '--user', '1000:1000']
    for k, v in (env or {}).items(): cmd += ['-e', k + '=' + v]
    for host, guest in (volumes or {}).items(): cmd += ['-v', str(host) + ':' + guest]
    docker(*cmd, image, *args)
    containers.append(full)
    return full
with tempfile.TemporaryDirectory(prefix='bitblik-smoke-') as tmp:
    root = Path(tmp)
    os.chmod(root, 0o755)
    for folder in ('coordinator', 'postgres', 'secrets'):
        d = root / 'data' / folder
        d.mkdir(parents=True)
        os.chown(d, 1000, 1000)
    subprocess.run(['bash', str(APP/'hooks/pre-start')], env=dict(os.environ, APP_DATA_DIR=tmp), check=True)
    docker('network', 'create', '--internal', name)
    try:
        pg = run('postgres', PG, env={'POSTGRES_USER':'postgres','POSTGRES_DB':'bitblik',
            'POSTGRES_PASSWORD_FILE':'/secrets/postgres-password'}, volumes={
            root/'data/postgres':'/var/lib/postgresql/data', root/'data/secrets':'/secrets:ro',
            APP/'hooks/init-db.sh':'/docker-entrypoint-initdb.d/10-bitblik.sh:ro'})
        for _ in range(60):
            if docker('exec',pg,'pg_isready','-U','postgres','-d','bitblik',check=False).returncode == 0: break
            time.sleep(1)
        else: raise RuntimeError('PostgreSQL did not become ready')
        coordinator = run('coordinator', COORD, args=('/bin/sh','/package/coordinator.sh'),
            volumes={root/'data/coordinator':'/state', root/'data/secrets':'/secrets:ro', APP/'hooks':'/package:ro'})
        time.sleep(2)
        assert 'disabled' in docker('logs',coordinator).stdout
        assert not (root/'data/coordinator/coordinator_private_key.hex').exists()
        docker('rm','-f',coordinator); containers.remove(coordinator)
        # Upstream runtime startup with no wallet and no external network. No activation
        # marker or macaroon; this bypasses wrapper ONLY in the disposable fixture.
        coordinator = run('coordinator', COORD, args=('/bin/sh','-c',
            'cd /state; export DB_PASSWORD="$(cat /secrets/db-password)"; exec /app/bin/bundle/bin/server'),
            env={'DB_HOST':'postgres','DB_PORT':'5432','DB':'bitblik','DB_USER':'bitblik',
                 'NOSTR_RELAYS':'ws://127.0.0.1:1','SIMPLEX_CHAT_EXEC':'','SIGNAL_CLI_EXEC':'',
                 'FLOW_DIR':'/app/flows'},
            volumes={root/'data/coordinator':'/state',root/'data/secrets':'/secrets:ro'})
        for _ in range(60):
            r = docker('exec',pg,'psql','-U','postgres','-d','bitblik','-Atc',
                       "SELECT count(*) FROM information_schema.tables WHERE table_name IN ('offers','log_audit')")
            if r.stdout.strip() == '2': break
            time.sleep(1)
        else: raise RuntimeError('Coordinator did not initialize schema')
        dashboard = run('dashboard', DASH, args=('/bin/sh','/package/dashboard.sh'),
            env={'DB_HOST':'postgres','DB_PORT':'5432','DB_NAME':'bitblik','DB_USER':'bitblik'},
            volumes={root/'data/secrets':'/secrets:ro',APP/'hooks':'/package:ro'})
        time.sleep(5)
        probe = "fetch('http://127.0.0.1:3001/').then(async r=>{if(!r.ok||!(await r.text()).includes('<html'))process.exit(1)}).catch(()=>process.exit(1))"
        docker('exec',dashboard,'node','-e',probe)
        assert 'Realtime listener connected' in docker('logs',dashboard).stdout
        docker('restart', dashboard)
        time.sleep(4)
        docker('exec',dashboard,'node','-e',probe)
        print('PASS: secret persistence, disabled startup, upstream schema, dashboard HTTP/realtime and dashboard restart')
    except Exception:
        for container in containers:
            logs = docker('logs','--tail','35',container,check=False)
            print(container, logs.stdout, logs.stderr)
        raise
    finally:
        for container in reversed(containers): docker('rm','-f',container,check=False)
        docker('network','rm',name,check=False)
