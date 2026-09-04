# Publishing audx

## Status (honest)

**Current package version: `0.3.0`** (see `pyproject.toml` / root `package.json`).

**Not published to PyPI under the name `audx`.** That name on PyPI is already taken by an
unrelated audio converter. Until a free name (or transfer) is secured, install from GitHub:

```bash
python -m pip install "git+https://github.com/chrisschouk/audx.git"
```

The root npm package is `"private": true` — dual npm+PyPI publish is aspirational, not live.

---

## Overview (when ready to publish)

Intended dual distribution:
- **Python package** (via pip/uv) — primary distribution for the CLI
- **npm package** — optional scoped name + JS wrapper

Both versions must keep version numbers in sync.

---

## Automated PyPI release (when name is available)

Releases are published by `.github/workflows/release.yml` using
**PyPI Trusted Publishing (OIDC)** — no API token is stored in the repo.

**One-time setup** (on PyPI, by the project owner):
1. Create a project on PyPI under an available name (not the occupied `audx` converter).
2. Add a *trusted publisher*: PyPI → project → Settings → Publishing →
   add GitHub, owner `chrisschouk`, repo `audx`, workflow `release.yml`,
   environment `pypi`. See https://docs.pypi.org/trusted-publishers/.
3. In GitHub repo settings, create an environment named `pypi`.
4. Update `pyproject.toml` / docs install lines to match the chosen name.

**Each release:**
```bash
# 1. bump version in pyproject.toml AND package.json (keep them in sync)
# 2. update CHANGELOG.md [Unreleased] -> the new version
git commit -am "release: audx v0.3.1"
git tag v0.3.1
git push origin main --tags        # the tag triggers the Release workflow
```

To build/inspect locally without publishing:
```bash
uv build            # -> dist/audx-<version>.tar.gz + .whl
uvx twine check dist/*
```

---

## Version Strategy

- **Major (X.0.0):** Breaking changes to CLI API
- **Minor (0.X.0):** New features, backwards-compatible
- **Patch (0.0.X):** Bug fixes, documentation updates

Current: `0.3.0` — terminal DAW + browser studio; not on PyPI yet.

---

## Troubleshooting

### PyPI name taken
Do **not** advertise `pip install audx` until this project owns that name.
Use a scoped/alternate name, or keep the git install path.

### npm package name
If publishing JS: use a scoped name such as `@chrisschouk/audx` and set
`package.json` `"private": false` only when ready.

### Python build fails
```bash
rm -rf dist/ build/ audx.egg-info/
uv run python -m build --clean
```
