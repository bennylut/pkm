from unittest import TestCase

from pkm.api.versions.version import Version, StandardVersion


class TestVersion(TestCase):

    def test_parsing(self):
        assert_version(Version.parse("2012.10"), "2012.10")
        assert_version(Version.parse("7.12rc5"), "7.12rc5")
        assert_version(Version.parse("7.12c5"), "7.12rc5")
        assert_version(Version.parse("12.4.post7"), "12.4.post7")
        assert_version(Version.parse("12.4a5.post7"), "12.4a5.post7")
        assert_version(Version.parse("7.9a3.dev7"), "7.9a3.dev7")
        assert_version(Version.parse("7.9a3.post5.dev7"), "7.9a3.post5.dev7")
        assert_version(Version.parse("7.9.post5.dev7"), "7.9.post5.dev7")
        assert_version(Version.parse("1!7.9.post5.dev7"), "1!7.9.post5.dev7")
        assert_version(Version.parse("1!1.2.3"), "1!1.2.3")
        assert_version(Version.parse("1!1.2.3a"), "1!1.2.3a0")
        assert_version(Version.parse("1.2-post2"), "1.2.post2")
        assert_version(Version.parse("1.2post2"), "1.2.post2")
        assert_version(Version.parse("1.2.post-2"), "1.2.post2")
        assert_version(Version.parse("1.0-r4"), "1.0.post4")
        assert_version(Version.parse("1.0-post"), "1.0.post0")
        assert_version(Version.parse("1.2-dev2"), "1.2.dev2")
        assert_version(Version.parse("1.2dev2"), "1.2.dev2")
        assert_version(Version.parse("1.2dev"), "1.2.dev0")
        assert_version(Version.parse("1.0+ubuntu-1"), "1.0+ubuntu.1")
        assert_version(Version.parse("v1.0+ubuntu-1"), "1.0+ubuntu.1")
        assert_version(Version.parse("1.0-1"), "1.0.post1")


    def test_version_comparison(self):
        v123 = StandardVersion((1, 2, 3))
        v200 = StandardVersion((2, 0, 0))
        v2 = StandardVersion((2,))

        assert v123 < v200, '1.2.3 expected to be before 2.0.0'
        assert v123 < v2, '1.2.3 expected to be before 2'
        assert v2 == v200, '2 expected to be equals to 2.0.0'


def assert_version(version: Version, expected_str: str) -> None:
    vstr = str(version)  # noqa
    assert vstr == expected_str, \
        f"unexpected version: {vstr} was expected to be {expected_str}"
