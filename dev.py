#!/usr/bin/env python3
"""Run all three services from ONE terminal.

    python dev.py            # start backend + settlement + frontend
    python dev.py --no-vite  # or skip any service you don't need
    Ctrl+C                   # stops everything cleanly

Each service's output is printed here with a [name] prefix. A Ctrl+C in
this terminal terminates all child processes.
"""
import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COLOR = sys.stdout.isatty()


def build_services(no_backend, no_settle, no_frontend):
    """Return [(name, argv, cwd, health_port), ...] in start order."""
    services = []
    if not no_backend:
        services.append((
            'django',
            [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'],
            ROOT / 'backend', 8000,
        ))
    if not no_settle:
        services.append((
            'settle',
            [sys.executable, '-m', 'uvicorn', 'main:app',
             '--host', '127.0.0.1', '--port', '8001'],
            ROOT / 'settlement_service', 8001,
        ))
    if not no_frontend:
        vite_js = ROOT / 'frontend' / 'node_modules' / 'vite' / 'bin' / 'vite.js'
        if vite_js.exists() and shutil.which('node'):
            argv = [shutil.which('node'), 'node_modules/vite/bin/vite.js']
        else:
            npm = shutil.which('npm') or ('npm.cmd' if os.name == 'nt' else 'npm')
            argv = [npm, 'run', 'dev']
        services.append(('vite', argv, ROOT / 'frontend', 5173))
    return services


def pump(name, stream):
    try:
        for raw in iter(stream.readline, b''):
            text = raw.decode('utf-8', 'replace').rstrip()
            if text:
                tag = f'[{name}]'
                if COLOR:
                    tag = f'\x1b[90m{tag:<9}\x1b[0m'
                print(f'{tag} {text}', flush=True)
    finally:
        stream.close()


def wait_until_up(port, timeout=60):
    """Return HTTP status once the server answers on port (any status
    counts as "up" — a refused connection raises instead)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/', timeout=2) as r:
                return r.status
        except urllib.error.HTTPError as e:
            return e.code  # server responded (e.g. 401 on /auth/login)
        except Exception:
            time.sleep(1)
    return None


def main():
    ap = argparse.ArgumentParser(description='Run all services in one terminal.')
    ap.add_argument('--no-backend', action='store_true', help='skip Django API')
    ap.add_argument('--no-settle', action='store_true', help='skip settlement service')
    ap.add_argument('--no-frontend', action='store_true', help='skip React frontend')
    args = ap.parse_args()

    services = build_services(args.no_backend, args.no_settle, args.no_frontend)
    procs = {}
    try:
        for name, argv, cwd, _port in services:
            print(f'starting {name}: {" ".join(argv)}', flush=True)
            p = subprocess.Popen(
                argv, cwd=str(cwd),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            procs[name] = p
            threading.Thread(target=pump, args=(name, p.stdout), daemon=True).start()

        print('waiting for services to come up...', flush=True)
        ok = True
        for name, _argv, _cwd, port in services:
            status = wait_until_up(port)
            if status is not None:
                print(f'[+] {name} is up on http://127.0.0.1:{port} (status {status})', flush=True)
            else:
                print(f'[-] {name} FAILED to come up on :{port} — see log above', flush=True)
                ok = False

        if ok and set(s[0] for s in services) == {'django', 'settle', 'vite'}:
            print('\nAll services running:')
            print('    Django API -> http://127.0.0.1:8000/api/auth/login/')
            print('    Settlement -> http://127.0.0.1:8001/health')
            print('    Frontend   -> http://127.0.0.1:5173')
        print('\nPress Ctrl+C to stop everything.', flush=True)

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('\nstopping all services...', flush=True)
    finally:
        for name, p in procs.items():
            if p.poll() is None:
                p.terminate()
        for name, p in procs.items():
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)
        print('done.', flush=True)


if __name__ == '__main__':
    main()