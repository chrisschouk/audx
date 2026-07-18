"""Sample library globals.

Covers the ``--samples`` override path: pointing the process-global library at a
directory must be the library the audio engine then resolves through.
"""

import audx.sampler as sampler
from audx.sampler import (
    SampleLibrary,
    get_sample_library,
    set_sample_library_root,
)


def test_get_sample_library_is_a_singleton():
    first = get_sample_library()
    assert get_sample_library() is first


def test_set_sample_library_root_overrides_the_global(tmp_path):
    lib = set_sample_library_root(tmp_path)
    assert isinstance(lib, SampleLibrary)
    assert lib.root == tmp_path
    # The engine reads through get_sample_library(), so the override must stick.
    assert get_sample_library() is lib
    assert get_sample_library().root == tmp_path


def test_set_sample_library_root_accepts_str(tmp_path):
    lib = set_sample_library_root(str(tmp_path / "kit"))
    assert lib.root == tmp_path / "kit"


def teardown_function():
    """Don't leak an overridden global into unrelated tests."""
    sampler._global_library = None
