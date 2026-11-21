"""Verify and pin the public 0.13.0-umbrel.2 image; does not push or deploy."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'rafftyl-custom-store-bitblik-coordinator'
REPO = 'ghcr.io/rafftyl/bitblik-coordinator'
VERSION = '0.13.0-umbrel.2'
REVISION = '0ae85a4537bac75b7ff1ab01dfe74b1795160e79'
OLD = 'ghcr.io/bit-blik/coordinator@sha256:50d4b501a33d2898324f9729a3b23d5a968207077acfcb3e1bdb5520ea50c7c0'


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def replacement(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f'Expected exactly one match for {old!r}; no files changed.')
    return text.replace(old, new)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('digest', help='The sha256 manifest digest printed by docker push')
    parser.add_argument('--expected-image-id', required=True,
                        help='Full image ID from the tested local build')
    args = parser.parse_args()
    for value in [args.digest, args.expected_image_id]:
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
            parser.error('Expected sha256: followed by 64 lowercase hex digits')

    ref = f'{REPO}@{args.digest}'
    compose, manifest, readme = (APP / name for name in
                                  ['docker-compose.yml', 'umbrel-app.yml', 'README.md'])
    new_compose = replacement(compose.read_text(encoding='utf-8'), OLD, ref)
    new_manifest = replacement(manifest.read_text(encoding='utf-8'),
                               'version: "0.13.0-umbrel.1"', f'version: "{VERSION}"')
    new_manifest = replacement(new_manifest, '''  Initial x86-64 preview: digest-pinned coordinator, PostgreSQL and monitoring
  dashboard. Explicit activation, persistent identity and restricted LND access.''',
                               '''  Adds an optional routing fee ceiling for new taker payouts. Existing payment
  attempts retain their saved fee limits; see the package README.''')
    old_readme = readme.read_text(encoding='utf-8')
    start = old_readme.index('Pinned registry images verified')
    end = old_readme.index('## 1. Install', start)
    new_readme = old_readme[:start] + f'''Pinned registry images:
- Coordinator: `{ref}`, custom x64 build at source revision `{REVISION}` (base `3311c2b`).
- Dashboard and PostgreSQL: unchanged from the initial package; see `docker-compose.yml`.

''' + old_readme[end:]

    # Empty client config ensures this is pullable without registry credentials.
    with tempfile.TemporaryDirectory() as config:
        print(docker('--config', config, 'pull', '--platform', 'linux/amd64', ref))
    image = json.loads(docker('image', 'inspect', ref))[0]
    if (image['Id'] != args.expected_image_id or image['Os'] != 'linux'
            or image['Architecture'] != 'amd64'
            or f'APP_VERSION={VERSION}' not in image['Config']['Env']
            or image['Config']['Labels'].get('org.opencontainers.image.revision') != REVISION):
        raise SystemExit('Image does not match tested image ID, platform or version; no files changed.')
    for path, content in [(compose, new_compose), (manifest, new_manifest), (readme, new_readme)]:
        path.write_text(content, encoding='utf-8', newline='\n')
    print(f'Pinned {ref}. Review the diff, then test and publish the store branch.')


if __name__ == '__main__':
    main()
