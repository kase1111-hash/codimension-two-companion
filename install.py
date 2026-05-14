#!/usr/bin/env python3
"""
install.py — Cross-platform dependency installer for the Codim-2 Companion.

Two layers of dependencies:

  1. Python packages (always installable via pip)
  2. Native libraries (libcairo via GTK+, pandoc, xelatex) — platform-specific

The installer does layer 1 automatically and reports layer 2 status with
copy-paste commands for whichever platform you're on.

Usage:
    python install.py              # install Python deps + check native deps
    python install.py --check      # check only, no install
    python install.py --no-cairo   # skip cairosvg (Windows users without GTK+)
    python install.py --quiet      # less verbose

Idempotent — safe to re-run.

Author: Kase Branham — Independent Researcher
"""

import argparse
import importlib
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# ─────────────────────────────────────────────────────────────────
# DEPENDENCY MANIFEST
# ─────────────────────────────────────────────────────────────────

# Python packages — (import_name, pip_name, why_needed)
PYTHON_DEPS = [
    ('yaml',      'pyyaml',    'spec.yaml parsing'),
    ('numpy',     'numpy',     'lattice + linear algebra'),
    ('tqdm',      'tqdm',      'progress bars'),
    ('rich',      'rich',      'live TUI dashboard'),
    ('certifi',   'certifi',   'SSL CA bundle (required on Windows for data_tools downloads)'),
]

PYTHON_DEPS_OPTIONAL = [
    ('cairosvg',  'cairosvg',  'SVG → PNG conversion (needs libcairo too)'),
]

# Native libraries — (probe_command, label, install_hints)
NATIVE_DEPS = [
    {
        'name':   'pandoc',
        'probe':  ['pandoc', '--version'],
        'why':    'Book build (Book.md → PDF/EPUB)',
        'optional': True,
        'install': {
            'Windows': 'winget install --id JohnMacFarlane.Pandoc',
            'Darwin':  'brew install pandoc',
            'Linux':   'sudo apt install pandoc      # Debian/Ubuntu\n'
                       '    sudo dnf install pandoc      # Fedora',
        },
    },
    {
        'name':   'xelatex',
        'probe':  ['xelatex', '--version'],
        'why':    'PDF rendering (TeX engine)',
        'optional': True,
        'install': {
            'Windows': '# Install MiKTeX:    https://miktex.org/download\n'
                       '    # Or TeX Live:       https://tug.org/texlive/',
            'Darwin':  'brew install --cask mactex',
            'Linux':   'sudo apt install texlive-xetex texlive-fonts-extra',
        },
    },
    {
        'name':   'libcairo (for cairosvg)',
        'probe_python': 'cairosvg',  # special-case: try cairosvg.svg2png
        'why':    'SVG → PNG render in ch_40 / ch_04 (purely cosmetic; SVG ships either way)',
        'optional': True,
        'install': {
            'Windows': 'winget install --id GTK.GTK3.runtime\n'
                       '    # Then reopen terminal so PATH updates.',
            'Darwin':  'brew install cairo',
            'Linux':   'sudo apt install libcairo2     # Debian/Ubuntu\n'
                       '    sudo dnf install cairo          # Fedora',
        },
    },
]


# ─────────────────────────────────────────────────────────────────
# OUTPUT
# ─────────────────────────────────────────────────────────────────

# Color codes — disable on Windows cmd if not a TTY
USE_COLOR = sys.stdout.isatty() and platform.system() != 'Windows'

def _c(code, text):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def ok(s):     return _c('92', s)  # green
def warn(s):   return _c('93', s)  # yellow
def fail(s):   return _c('91', s)  # red
def bold(s):   return _c('1', s)
def dim(s):    return _c('2', s)
def header(s):
    print()
    print('=' * 70)
    print(f'  {bold(s)}')
    print('=' * 70)


# ─────────────────────────────────────────────────────────────────
# CHECKS
# ─────────────────────────────────────────────────────────────────

def check_python_version():
    """Require Python 3.9+."""
    major, minor = sys.version_info[:2]
    if (major, minor) < (3, 9):
        print(fail(f"  ✗ Python {major}.{minor} found — need 3.9 or newer."))
        return False
    print(f"  {ok('✓')} Python {major}.{minor}.{sys.version_info[2]} "
          f"({sys.executable})")
    return True


def check_python_pkg(import_name: str) -> bool:
    """Return True if the package is installed and importable.
    
    Some packages (notably cairosvg) raise OSError at import time when their
    native backing library is missing. We treat that as 'installed but with
    native trouble' — the package IS present, the native lib issue is reported
    separately by check_cairo_via_cairosvg().
    """
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False
    except (OSError, Exception):
        # cairosvg → OSError when libcairo missing.
        # Other packages might raise different errors at import. Either way,
        # the package files exist on disk (pip put them there); treat as present.
        return True


def check_cairo_via_cairosvg() -> tuple:
    """Special case: cairosvg installs fine but libcairo dlopen may fail.
    
    On Windows without GTK+, `import cairosvg` itself raises OSError at module
    load time (cairocffi's dlopen runs at import). We treat that as "package
    installed, native lib missing".
    
    Returns (installed_on_disk, dlopen_works)."""
    try:
        import cairosvg
    except ImportError:
        return (False, False)
    except OSError:
        # The pip package is on disk; cairocffi just can't dlopen libcairo.
        return (True, False)
    # Import succeeded — try the actual conversion path to be safe
    try:
        out = (Path.home() / '_cairo_probe.png') if platform.system() == 'Windows' \
              else Path('/tmp/_cairo_probe.png')
        cairosvg.svg2png(
            bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>',
            write_to=str(out))
        try:
            out.unlink()
        except OSError:
            pass
        return (True, True)
    except (OSError, Exception):
        return (True, False)


def check_native(cmd: list) -> bool:
    """Probe a binary by running --version. Returns True if found."""
    bin_name = cmd[0]
    if shutil.which(bin_name) is None:
        return False
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=10)
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


# ─────────────────────────────────────────────────────────────────
# INSTALL
# ─────────────────────────────────────────────────────────────────

def pip_install(packages: list, verbose: bool = True) -> bool:
    """Install via pip. Uses --user if the global install would fail."""
    if not packages:
        return True
    cmd = [sys.executable, '-m', 'pip', 'install']
    if verbose:
        print(f"\n  Installing: {' '.join(packages)}")
    cmd.extend(packages)
    try:
        r = subprocess.run(cmd, capture_output=not verbose)
        if r.returncode != 0 and 'externally-managed' in (r.stderr or b'').decode('utf-8', errors='replace'):
            # PEP 668 — Debian/Ubuntu blocks system pip. Retry with --break-system-packages.
            print(warn("  System Python is externally managed; "
                       "retrying with --break-system-packages ..."))
            cmd2 = cmd + ['--break-system-packages']
            r = subprocess.run(cmd2, capture_output=not verbose)
        return r.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(fail(f"  pip install failed: {e}"))
        return False


# ─────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--check', action='store_true',
                        help='Check only, do not install anything')
    parser.add_argument('--no-cairo', action='store_true',
                        help='Skip cairosvg (Windows without GTK+)')
    parser.add_argument('--quiet', action='store_true', help='Less verbose')
    args = parser.parse_args()
    
    plat = platform.system()
    
    header('Codim-2 Companion — Dependency Installer')
    print(f"  Platform: {plat} ({platform.release()}) · "
          f"Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # ── Python version ──────────────────────────────────────────
    if not check_python_version():
        print(fail("\n  Abort: Python 3.9+ required."))
        return 1
    
    # ── Python packages ─────────────────────────────────────────
    header('Python packages')
    missing_required = []
    for imp, pip_name, why in PYTHON_DEPS:
        if check_python_pkg(imp):
            print(f"  {ok('✓')} {pip_name:<12} ({why})")
        else:
            print(f"  {fail('✗')} {pip_name:<12} ({why}) — {bold('missing')}")
            missing_required.append(pip_name)
    
    missing_optional = []
    if not args.no_cairo:
        for imp, pip_name, why in PYTHON_DEPS_OPTIONAL:
            if check_python_pkg(imp):
                print(f"  {ok('✓')} {pip_name:<12} ({why})")
            else:
                print(f"  {warn('·')} {pip_name:<12} ({why}) — {dim('optional, missing')}")
                missing_optional.append(pip_name)
    
    if missing_required or missing_optional:
        to_install = missing_required + missing_optional
        if args.check:
            print(warn(f"\n  --check mode: would install {to_install}"))
        else:
            if pip_install(to_install, verbose=not args.quiet):
                print(ok(f"\n  ✓ Installed: {' '.join(to_install)}"))
            else:
                print(fail(f"\n  ✗ pip install failed. Try manually:"))
                print(f"      {sys.executable} -m pip install {' '.join(to_install)}")
                return 1
    else:
        print(ok("\n  All Python packages present."))
    
    # ── Native libraries ────────────────────────────────────────
    header('Native libraries')
    print("  (These need OS-level installation. Pip cannot install them.)\n")
    
    all_native_ok = True
    for dep in NATIVE_DEPS:
        if dep['name'] == 'libcairo (for cairosvg)':
            if args.no_cairo:
                continue
            importable, dlopen_works = check_cairo_via_cairosvg()
            if not importable:
                # cairosvg not even installed; covered in Python section above
                print(f"  {dim('·')} {dep['name']:<22} ({dep['why']}) — "
                      f"{dim('cairosvg not installed; skip')}")
                continue
            if dlopen_works:
                print(f"  {ok('✓')} {dep['name']:<22} ({dep['why']})")
                continue
            # importable but dlopen fails — typical Windows missing-GTK case
            status_msg = warn('libcairo not found by cairosvg')
        elif 'probe' in dep:
            if check_native(dep['probe']):
                print(f"  {ok('✓')} {dep['name']:<22} ({dep['why']})")
                continue
            status_msg = warn('not found on PATH')
        else:
            continue
        
        # Report missing with install hint
        marker = warn('!') if dep.get('optional') else fail('✗')
        print(f"  {marker} {dep['name']:<22} ({dep['why']}) — {status_msg}")
        hint = dep['install'].get(plat)
        if hint:
            for line in hint.split('\n'):
                print(f"      {dim(line)}")
        if not dep.get('optional'):
            all_native_ok = False
    
    # ── Verify pipeline can run ────────────────────────────────
    header('Pipeline smoke test')
    project_root = Path(__file__).parent
    if not (project_root / 'pipeline' / 'registry.py').exists():
        print(warn(f"  · Not in a Codim2_Companion checkout (no pipeline/registry.py); "
                   f"skipping smoke test."))
    else:
        try:
            sys.path.insert(0, str(project_root / 'pipeline'))
            from registry import discover_steps
            steps = discover_steps()
            n = len(steps)
            if n >= 39:
                print(f"  {ok('✓')} {n} pipeline steps discovered.")
            else:
                print(f"  {warn('!')} Only {n} steps discovered (expected ≥39). "
                      f"YAML parse errors?")
        except Exception as e:
            print(f"  {fail('✗')} Smoke test failed: {type(e).__name__}: {e}")
            all_native_ok = False
    
    # ── Final summary ──────────────────────────────────────────
    header('Summary')
    if missing_required and not args.check:
        # missing_required got installed above; re-check
        still_missing = [n for n in missing_required if not check_python_pkg(
            next(imp for imp, pn, _ in PYTHON_DEPS if pn == n))]
        if still_missing:
            print(fail(f"  ✗ Required packages still missing: {still_missing}"))
            return 1
    
    print(f"  {ok('✓')} Required Python packages installed.")
    print(f"\n  {bold('Next steps:')}")
    print(f"    python -m pipeline.runner --list           # see all 39 steps")
    print(f"    python -m pipeline.runner --all -- --quick # run pipeline")
    print(f"    python -m pipeline.tui                     # live dashboard")
    if any(check_native(d.get('probe', [''])) is False for d in NATIVE_DEPS
           if 'probe' in d and d['name'] in ('pandoc', 'xelatex')):
        print(f"\n  {dim('  (Install pandoc + xelatex if you want to build the book PDF/EPUB.)')}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
