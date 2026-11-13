"""Read-only validation plus disposable Docker integration; never uses a wallet."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'rafftyl-custom-store-bitblik-coordinator'
COMPOSE = yaml.safe_load((APP / 'docker-compose.yml').read_text())

class PackageTests(unittest.TestCase):
    def test_shell_syntax(self):
        for path in (APP / 'hooks').iterdir():
            subprocess.run(['bash', '-n', str(path)], check=True)

    def test_security_boundaries(self):
        services = COMPOSE['services']
        self.assertEqual(services['app_proxy']['environment']['PROXY_AUTH_ADD'], 'true')
        for name in ('postgres', 'coordinator', 'dashboard'):
            self.assertNotIn('ports', services[name])
            self.assertIn('@sha256:', services[name]['image'])
            self.assertNotIn('privileged', services[name])
        coordinator = json.dumps(services['coordinator'])
        self.assertNotIn('admin.macaroon', coordinator)
        self.assertNotIn('docker.sock', coordinator)
        self.assertIn('/tls.cert:', coordinator)
        self.assertEqual(services['coordinator']['working_dir'], '/state')
        self.assertNotIn('NOSTR_PRIVATE_KEY', coordinator)

    def test_compose_renders(self):
        env = dict(os.environ, APP_DATA_DIR='/tmp/bitblik-test',
                   APP_LIGHTNING_NODE_IP='10.21.21.9',
                   APP_LIGHTNING_NODE_GRPC_PORT='10009',
                   APP_LIGHTNING_NODE_DATA_DIR='/tmp/synthetic-lnd')
        with tempfile.TemporaryDirectory() as tmp:
            overlay = Path(tmp) / 'umbrel-proxy.yml'
            overlay.write_text('services:\n  app_proxy:\n    image: synthetic-umbrel-proxy:fixture\n')
            subprocess.run(['docker', 'compose', '-f', str(APP / 'docker-compose.yml'),
                            '-f', str(overlay), 'config', '--quiet'], env=env, check=True)

    def test_preparation_idempotent_and_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix='bitblik-prep-') as tmp:
            data = Path(tmp)
            for name in ('coordinator', 'secrets', 'postgres'):
                folder = data / 'data' / name
                folder.mkdir(parents=True)
                os.chown(folder, 1000, 1000)
            env = dict(os.environ, APP_DATA_DIR=tmp)
            command = ['bash', str(APP / 'hooks/pre-start')]
            subprocess.run(command, env=env, check=True)
            secret = data / 'data/secrets/db-password'
            before = secret.read_bytes()
            subprocess.run(command, env=env, check=True)
            self.assertEqual(before, secret.read_bytes())
            self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
            self.assertFalse((data / 'data/coordinator/ENABLED').exists())
            (data / 'data/postgres/PG_VERSION').write_text('16')
            secret.unlink()
            self.assertNotEqual(subprocess.run(command, env=env, capture_output=True).returncode, 0)
            self.assertFalse(secret.exists())

if __name__ == '__main__':
    unittest.main()
