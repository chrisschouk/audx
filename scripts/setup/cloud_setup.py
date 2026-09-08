#!/usr/bin/env python3
"""Portable cloud setup contract v1. No provider or financial operations."""
import argparse
import json
import os
import io
import hashlib
import platform
import tarfile
import urllib.request
from pathlib import Path
import shutil
import subprocess
import sys


# Recorded 8 September 2026 from upstream GitHub release asset digests and Node SHASUMS256.txt.
ARCHIVE_SHA256 = {
    "gh_2.100.0_linux_amd64.tar.gz": "e4d4bb4498e8d007abe545b6568926793ace1b6447da598294a610018cb164be",
    "gh_2.100.0_linux_arm64.tar.gz": "ea4e7a581a32ccad6cc7923cb1576ac5859ba4b9a16ab22eb8f8a96e78e2e961",
    "gitleaks_8.30.1_linux_x64.tar.gz": "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    "gitleaks_8.30.1_linux_arm64.tar.gz": "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
    "supabase_2.116.0_linux_amd64.tar.gz": "5b3031cb297d51b25be4c284e4c852254460ec722ec221d3b81b07d55acfd158",
    "supabase_2.116.0_linux_arm64.tar.gz": "015a45756bb8459716a4b44b020605adc11956cd7d0bd5824aec2ed1c8287933",
    "uv-x86_64-unknown-linux-gnu.tar.gz": "ec7a99cd05e0cd7f80243f135ce1361c76835cb0ee60055d14d20eba8eba1460",
    "uv-aarch64-unknown-linux-gnu.tar.gz": "c36fe17937ff6bd16dc42fc13854b5465999fcab2efe0af559381e945e3c6001",
    "node-v22.23.2-linux-x64.tar.xz": "d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307",
    "node-v22.23.2-linux-arm64.tar.xz": "fff4078c5def658577f92c88db7db3bc0072924bfb93fe52c1e744a54e94abb8"
}

def verify_archive(name, payload):
    if hashlib.sha256(payload).hexdigest() != ARCHIVE_SHA256.get(name):
        raise ValueError('archive checksum mismatch')


def download_archive(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = response.read(150_000_001)
    if len(payload) > 150_000_000:
        raise ValueError('archive limit')
    verify_archive(url.rsplit('/', 1)[1], payload)
    return payload


def run(command, cwd):
    # Captured output can contain registry credentials: never echo it.
    try:
        return subprocess.run(command, cwd=cwd, stdin=subprocess.DEVNULL,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              timeout=600, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def install_tools(root, python_projects=False):
    """Pinned upstream Linux binaries; extract regular named files only."""
    if platform.system() != 'Linux':
        print('tool installation: unavailable (Linux cloud hosts only)')
        return False
    arch = {'x86_64': 'amd64', 'aarch64': 'arm64'}.get(platform.machine())
    if not arch:
        print('tool installation: unavailable (unsupported architecture)')
        return False
    target = Path.home() / '.local' / 'bin'
    target.mkdir(parents=True, exist_ok=True)
    os.environ['PATH'] = str(target) + os.pathsep + os.environ['PATH']
    # Node's official distribution includes npm; no shell profile or global install changes.
    if not shutil.which('node') or not shutil.which('npm'):
        node_arch = 'x64' if arch == 'amd64' else 'arm64'
        node_name = f'node-v22.23.2-linux-{node_arch}'
        node_dir = target.parent / 'share/cloud-setup'
        node_dir.mkdir(parents=True, exist_ok=True)
        try:
            payload = download_archive(f'https://nodejs.org/dist/v22.23.2/{node_name}.tar.xz')
            with tarfile.open(fileobj=io.BytesIO(payload), mode='r:xz') as archive:
                archive.extractall(node_dir, filter='data')
            for name in ('node', 'npm', 'npx'):
                if not (target / name).exists():
                    (target / name).symlink_to(node_dir / node_name / 'bin' / name)
        except Exception:
            print('node/npm: unavailable (pinned runtime install failed; requires Python with tar data filter)')
            return False
    releases = {
        'gh': f'https://github.com/cli/cli/releases/download/v2.100.0/gh_2.100.0_linux_{arch}.tar.gz',
        'gitleaks': f'https://github.com/gitleaks/gitleaks/releases/download/v8.30.1/gitleaks_8.30.1_linux_{"x64" if arch == "amd64" else "arm64"}.tar.gz',
        'supabase': f'https://github.com/supabase/cli/releases/download/v2.116.0/supabase_2.116.0_linux_{arch}.tar.gz',
    }
    if python_projects:
        uv_arch = 'x86_64' if arch == 'amd64' else 'aarch64'
        releases['uv'] = f'https://github.com/astral-sh/uv/releases/download/0.12.9/uv-{uv_arch}-unknown-linux-gnu.tar.gz'
    ok = True
    for tool, url in releases.items():
        if shutil.which(tool):
            continue
        try:
            payload = download_archive(url)
            with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
                matches = [m for m in archive.getmembers() if m.isfile() and Path(m.name).name == tool]
                if len(matches) != 1:
                    raise ValueError('unexpected archive')
                data = archive.extractfile(matches[0]).read()
            (target / tool).write_bytes(data)
            (target / tool).chmod(0o755)
        except Exception:
            print(f'{tool}: unavailable (pinned upstream download or extraction failed)')
            ok = False
    if not shutil.which('vercel'):
        installed = run(['npm', 'install', '--prefix', str(target.parent), '--ignore-scripts', '--no-audit', '--no-fund', 'vercel@59.11.7'], root)
        executable = target.parent / 'node_modules/.bin/vercel'
        if installed and executable.exists() and not (target / 'vercel').exists():
            (target / 'vercel').symlink_to(executable)
        ok = installed and ok
    print('session PATH: include ~/.local/bin in the cloud environment PATH')
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-environment', action='store_true', help='fail if a declared task-specific environment variable is missing')
    parser.add_argument('--sync-context', action='store_true', help='sync shared commands and direct skill dependencies from TAP')
    parser.add_argument('--install-tools', action='store_true', help='install missing pinned Linux cloud CLIs')
    parser.add_argument('--install', action='store_true', help='install locked dependencies; lifecycle scripts disabled')
    args = parser.parse_args()
    setup = Path(__file__).resolve().parent
    root = setup.parent.parent
    config = json.loads((setup / 'cloud-contract.json').read_text())
    python_projects = any(p['manager'] == 'uv' for p in config['projects'])
    failed = args.install_tools and not install_tools(root, python_projects)
    def report(name, status, detail):
        print(f'{name}: {status} ({detail})')
    for tool in ('git', 'python3', 'node', 'npm', 'gh', 'gitleaks', 'supabase', 'vercel'):
        present = shutil.which(tool) is not None
        valid = present and run([tool, 'version' if tool == 'gitleaks' else '--version'], root)
        report(tool, 'verified' if valid else 'unavailable', 'version command only; auth untested' if valid else 'missing or version command failed')
        if not valid:
            failed = True
    for project in config['projects']:
        directory = root / project['path']
        manager = project['manager']
        if manager == 'uv':
            if not (directory / 'pyproject.toml').is_file() or not (directory / 'uv.lock').is_file():
                report(project['path'], 'unavailable', 'Python manifest or uv.lock missing; refusing unlocked install')
                failed = True
                continue
            if not shutil.which('uv') or not run(['uv', '--version'], root):
                report('uv', 'unavailable', 'use --install-tools on Linux')
                failed = True
                continue
            if args.install:
                ok = run(['uv', 'sync', '--frozen', '--no-install-project', '--no-build'], directory)
                report(project['path'] + ' dependencies', 'verified' if ok else 'unavailable', 'locked Python dependencies; project install and source builds disabled' if ok else 'uv sync failed; output withheld')
                failed = failed or not ok
            else:
                report(project['path'] + ' dependencies', 'untested', 'uv.lock present; run --install in cloud checkout')
            continue
        executable = manager.split('@')[0]
        manifest = json.loads((directory / 'package.json').read_text())
        declared = manifest.get('packageManager', manager)
        if declared != manager:
            report(project['path'], 'unavailable', 'packageManager differs from cloud-contract.json')
            failed = True
            continue
        lock = directory / ('pnpm-lock.yaml' if executable == 'pnpm' else 'package-lock.json')
        if not lock.is_file():
            report(project['path'], 'unavailable', 'lockfile missing; refusing unlocked install')
            failed = True
            continue
        if executable == 'pnpm':
            version = manager.split('@', 1)[1]
            # Use the pinned package manager without replacing the host global install.
            local = Path(os.environ.get('CLOUD_SETUP_TOOLS_DIR', str(Path.home() / '.local/share/cloud-setup'))) / manager
            pinned = local / 'node_modules' / '.bin' / 'pnpm'
            if args.install and not pinned.exists():
                if not run(['npm', 'install', '--prefix', str(local), '--ignore-scripts', '--no-audit', '--no-fund', manager], root):
                    report(manager, 'unavailable', 'package manager install failed')
                    failed = True
                    continue
            command = str(pinned) if pinned.exists() else executable
            try:
                actual = subprocess.check_output([command, '--version'], cwd=root, stderr=subprocess.DEVNULL, timeout=20, text=True).strip()
            except (OSError, subprocess.SubprocessError):
                actual = ''
            if actual != version:
                report(manager, 'unavailable', 'pinned version not available; use --install')
                failed = True
                continue
        else:
            command = executable
        if args.install:
            options = ['install', '--frozen-lockfile', '--ignore-scripts'] if executable == 'pnpm' else ['ci', '--ignore-scripts', '--no-audit', '--no-fund']
            ok = run([command, *options], directory)
            report(project['path'] + ' dependencies', 'verified' if ok else 'unavailable', 'locked install; lifecycle scripts disabled' if ok else 'install failed; output withheld to protect credentials')
            failed = failed or not ok
        else:
            report(project['path'] + ' dependencies', 'untested', 'lockfile present; run --install in cloud checkout')
    if args.sync_context:
        synced = run(['bash', str(setup / 'ensure-commands.sh')], root)
        commands = Path(os.environ.get('CLAUDE_CMD_DIR', str(Path.home() / '.claude/commands')))
        skills = Path(os.environ.get('CLAUDE_SKILL_DIR', str(Path.home() / '.claude/skills')))
        synced = synced and all((commands / name).is_file() for name in ('start.md', 'done.md', 'ship.md', 'checkpoint.md', 'weekly-review.md', 'start-reference.md'))
        synced = synced and all((skills / name / 'SKILL.md').is_file() for name in ('brand-voice-guide', 'commodity-gate', 'home'))
        report('shared command context', 'verified' if synced else 'unavailable', 'files present; task-specific command runtime untested')
        failed = failed or not synced
    for name in config['environment']:
        if args.require_environment and not os.environ.get(name):
            failed = True
        report(name, 'untested' if os.environ.get(name) else 'unavailable', 'configured; no provider request made' if os.environ.get(name) else 'not configured')
    report('application, providers, cloud activation', 'untested', 'setup does not build, test, deploy, send, spend, ingest or load private financial data')
    return 2 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
