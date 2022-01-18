from unittest import TestCase
from pkm.api.versions.version_specifiers import *
from pkm.api.versions.version import *

parse = VersionSpecifier.parse


class TestVersionSpecifiers(TestCase):

    def test_allows(self):
        vs_range = parse('>= 1.1')
        vs_spec = parse('== 1.2+local-label')

        vlocal = Version.parse('1.2+local-label')
        vpost = Version.parse('1.2-1')
        v = Version.parse('1.2')

        assert not vs_range.allows_version(vlocal)
        assert not vs_range.allows_version(vpost)
        assert vs_range.allows_version(v)
        assert vs_spec.allows_version(vlocal)

        # rules exceptions:
        assert VersionSpecifier.parse('>1.7.post1').allows_version(Version.parse('1.7-2'))
        assert VersionSpecifier.parse('<1.7a5').allows_version(Version.parse('1.7a'))

        # regression
        assert VersionSpecifier.parse("<1").union(VersionSpecifier.parse(">=2")).allows_all(
            VersionSpecifier.parse("==2.0.0"))

    def test_parsing(self):
        assert_spec(parse("== 1.1"), "==1.1")
        assert_spec(parse("== 1.1.post1"), "==1.1.post1")
        assert_spec(parse("== 1.1.*"), ">=1.1, <1.2")
        assert_spec(parse("~= 2.2"), ">=2.2, <3.0")
        assert_spec(parse("~= 1.4.5"), ">=1.4.5, <1.5.0")
        assert_spec(parse("!= 1.1"), "!=1.1")
        assert_spec(parse("!= 1.1.*"), "<1.1; >=1.2")
        assert_spec(parse(">1.7"), '>1.7')
        assert_spec(parse(">1.7.post2"), '>1.7.post2')
        assert_spec(parse("=== bamba"), '===bamba')
        assert_spec(parse(">1,<2"), '>1, <2')
        assert_spec(parse(">1,<2,==5"), '<none>')
        assert_spec(parse(">1,<2,*"), '>1, <2')
        assert_spec(parse("(>=1.17.3)"), '>=1.17.3')
        assert_spec(parse(">= '2.7'"), '>=2.7')

    def test_version_set_operations(self):
        v1 = SpecificVersion(StandardVersion((1, 2, 3)))
        assert_spec(v1.inverse(), '!=1.2.3')
        assert_spec(v1.union(v1), '==1.2.3')
        assert_spec(v1.difference(v1), '<none>')

        v2 = SpecificVersion(StandardVersion((1, 2, 4)))
        assert_spec(v1.union(v2), '==1.2.3, ==1.2.4')
        assert_spec(v1.intersect(v2), '<none>')
        assert_spec(v1.union(v2).intersect(v1), '==1.2.3')
        assert_spec(v1.difference(v2), '==1.2.3')

    def test_range_set_operations(self):
        v1 = SpecificVersion(StandardVersion((1, 2, 3)))
        r1 = VersionRange(min=v1)

        assert_spec(r1, '>1.2.3')
        assert_spec(r1.inverse(), '<=1.2.3')

        v2 = SpecificVersion(StandardVersion((2, 0, 0)))
        assert_spec(r1.union(v2), '>1.2.3')
        assert_spec(v2.union(r1), '>1.2.3')

        r2 = VersionRange(max=v1, includes_max=True)
        assert_spec(r1.union(r2), '*')

        r3 = VersionRange(min=v1, max=v2)
        assert_spec(AnyVersion.difference(r3).union(r3), '*')

        assert_spec(VersionSpecifier.parse('>=2, <3').inverse(), '<2; >=3')

        # >=0.3.1, <=0.3.3 intersect with <=0.3.2; >=1.0.0
        u = parse('<=0.3.2').union(parse('>=1.0.0'))
        assert_spec(u, '<=0.3.2; >=1.0.0')
        assert_spec(parse('>=0.3.1, <=0.3.3').intersect(u), '>=0.3.1, <=0.3.2')

    def test_star_operations(self):
        all_ = AnyVersion
        v1 = SpecificVersion(StandardVersion((1, 0, 0)))

        assert_spec(all_.difference(v1), '!=1.0.0')
        assert_spec(all_.intersect(v1), '==1.0.0')
        assert_spec(all_.union(v1), '*')

        r1 = VersionRange(v1, SpecificVersion(StandardVersion((2, 0, 0))))
        assert_spec(all_.difference(r1), '<=1.0.0, >=2.0.0')

        assert_spec(all_.inverse().inverse(), '*')


def assert_spec(version: VersionSpecifier, expected_str: str) -> None:
    vstr = str(version)  # noqa
    assert vstr == expected_str, \
        f"unexpected version: {vstr} was expected to be {expected_str}"
