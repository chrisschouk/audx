"""Config directory resolution.

These lock in the cross-platform contract: audx must place its config, samples,
and projects directories where each OS expects them, honour explicit env-var
overrides, and never touch the disk merely because a module was imported.
"""

import importlib
from pathlib import Path

import pytest

import audx.config as config

_ENV_VARS = (
    "AUDX_CONFIG_DIR",
    "AUDX_SAMPLES_DIR",
    "AUDX_PROJECTS_DIR",
    "XDG_CONFIG_HOME",
    "APPDATA",
)


@pytest.fixture
def clean_env(monkeypatch):
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture(autouse=True)
def _restore_config_module():
    """Any test that reloads config or patches ``Path.home`` must leave the
    real module state behind for the rest of the session."""
    yield
    importlib.reload(config)


def test_import_has_no_disk_side_effects(monkeypatch, tmp_path):
    """Importing config must not create any directories on its own."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    importlib.reload(config)
    assert list(home.iterdir()) == []


def test_linux_uses_xdg(clean_env):
    assert config._config_dir(platform="linux", os_name="posix") == \
        config.HOME / ".config" / "audx"


def test_linux_respects_xdg_config_home(clean_env, tmp_path):
    clean_env.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    assert config._config_dir(platform="linux", os_name="posix") == \
        tmp_path / "xdg" / "audx"


def test_macos_uses_application_support(clean_env):
    assert config._config_dir(platform="darwin", os_name="posix") == \
        config.HOME / "Library" / "Application Support" / "audx"


def test_windows_uses_appdata(clean_env, tmp_path):
    clean_env.setenv("APPDATA", str(tmp_path / "roaming"))
    assert config._config_dir(platform="win32", os_name="nt") == \
        tmp_path / "roaming" / "audx"


@pytest.mark.parametrize(
    "var,func",
    [
        ("AUDX_CONFIG_DIR", "_config_dir"),
        ("AUDX_SAMPLES_DIR", "_samples_dir"),
        ("AUDX_PROJECTS_DIR", "_projects_dir"),
    ],
)
def test_env_override_wins(clean_env, tmp_path, var, func):
    target = tmp_path / "override"
    clean_env.setenv(var, str(target))
    assert getattr(config, func)() == target


def test_env_override_expands_tilde(clean_env):
    clean_env.setenv("AUDX_SAMPLES_DIR", "~/my-samples")
    assert config._samples_dir() == Path.home() / "my-samples"
