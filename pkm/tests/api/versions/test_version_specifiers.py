from unittest import TestCase

from pkm.api.versions.version_parser import parse_version, parse_specifier
from pkm.api.versions.version_specifiers import *

spec = parse_specifier
ver = parse_version


class TestVersionSpecifiers(TestCase):

    def test_inverse(self):
        version = spec(">=0.14.0, <0.17.0") \
            .union_with(spec(">0.17.0, <0.17.1")) \
            .union_with(spec(">0.17.1, <0.17.2")) \
            .union_with(spec(">0.17.2"))

        assert_spec(version.inverse(), "<0.14.0; ==0.17.0; ==0.17.1; ==0.17.2")

    def test_locals(self):
        local_version = spec("==1.0.0+local")
        version = spec("==1.0.0")

        assert_spec(local_version.intersect_with(version), "==1.0.0+local")

        assert spec("==1.0.0").allows_any(local_version)
        assert not spec("==1.0.0+otherlocal").allows_any(local_version)

        assert not spec("!=1.0.0").allows_version(ver("1.0.0+local"))
        assert not spec("!=1.0.0").allows_all(spec("==1.0.0+local"))

    def test_allows(self):
        vs_range = spec('>= 1.1')
        vs_spec = spec('== 1.2+local-label')

        vlocal = Version.parse('1.2+local-label')
        vpost = Version.parse('1.2-1')
        v = Version.parse('1.2')

        assert vs_range.allows_version(vlocal)
        assert not vs_range.allows_version(vpost)
        assert vs_range.allows_version(v)
        assert vs_spec.allows_version(vlocal)

        # rules exceptions:
        assert spec('>1.7.post1').allows_version(Version.parse('1.7-2'))
        assert spec('<1.7a5').allows_version(Version.parse('1.7a'))

        # edge cases
        assert spec("<2.0").allows_all(RestrictAllVersions)

        # regression
        assert spec("<1").union_with(spec(">=2")).allows_all(spec("==2.0.0"))

        s = spec("!=3.0.5, >=2.0.2")
        assert s.allows_all(s)
        assert not s.allows_any(s.inverse())

        assert spec(">5.4.0, <8.2.0").allows_all(spec(">=7.2.0, <=7.5.0"))
        assert spec('>1.0.1').allows_all(spec('>=1.1.0, <1.1.1'))

    def test_parsing(self):
        assert_spec(spec("== 1.1"), "==1.1")
        assert_spec(spec("== 1.1.post1"), "==1.1.post1")
        assert_spec(spec("== 1.1.*"), ">=1.1, <1.2")
        assert_spec(spec("~= 2.2"), ">=2.2, <3.0")
        assert_spec(spec("~= 1.4.5"), ">=1.4.5, <1.5.0")
        assert_spec(spec("!= 1.1"), "!=1.1")
        assert_spec(spec("!= 1.1.*"), "<1.1; >=1.2")
        assert_spec(spec(">1.7"), '>1.7')
        assert_spec(spec(">1.7.post2"), '>1.7.post2')
        assert_spec(spec("=== bamba"), '===bamba')
        assert_spec(spec(">1,<2"), '>1, <2')
        assert_spec(spec(">1,<2,==5"), '<none>')
        assert_spec(spec(">1,<2,*"), '>1, <2')
        assert_spec(spec("(>=1.17.3)"), '>=1.17.3')
        assert_spec(spec(">= '2.7'"), '>=2.7')

    def test_mix_set_operations(self):
        assert_spec(spec("!=1.8, !=1.8.1").intersect_with(spec("<1.9.0")), "!=1.8, !=1.8.1, <1.9.0")

    def test_version_set_operations(self):
        v1 = spec("==1.2.3")
        assert_spec(v1.inverse(), '!=1.2.3')
        assert_spec(v1.union_with(v1), '==1.2.3')
        assert_spec(v1.difference_from(v1), '<none>')

        v2 = spec("==1.2.4")
        assert_spec(v1.union_with(v2), '==1.2.3; ==1.2.4')
        assert_spec(v1.intersect_with(v2), '<none>')
        assert_spec(v1.union_with(v2).intersect_with(v1), '==1.2.3')
        assert_spec(v1.difference_from(v2), '==1.2.3')
        assert_spec(spec("<2.0").intersect_with(RestrictAllVersions), '<none>')


    def test_range_set_operations(self):
        v1 = ver("1.2.3")
        v2 = ver("2.0.0")

        r1 = spec(f">{v1}")

        assert_spec(r1, '>1.2.3')
        assert_spec(r1.inverse(), '<=1.2.3')

        r2 = spec(f"=={v2}")
        assert_spec(r1.union_with(r2), '>1.2.3')
        assert_spec(r2.union_with(r1), '>1.2.3')

        r3 = spec(f"<={v1}")
        assert_spec(r1.union_with(r3), '*')

        r4 = spec(f">{v1},<{v2}")

        assert_spec(AllowAllVersions.difference_from(r4).union_with(r4), '*')

        assert_spec(spec('>=2, <3').inverse(), '<2; >=3')

        # >=0.3.1, <=0.3.3 intersect with <=0.3.2; >=1.0.0
        u = spec('<=0.3.2').union_with(spec('>=1.0.0'))
        assert_spec(u, '<=0.3.2; >=1.0.0')
        assert_spec(spec('>=0.3.1, <=0.3.3').intersect_with(u), '>=0.3.1, <=0.3.2')

        assert_spec(spec(">=4.62").intersect_with(spec(">=4.62,<4.65")), ">=4.62, <4.65")
        assert_spec(spec("<=5.4.0").union_with(spec(">=7.3.0, <=8.2.0")))

    def test_star_operations(self):
        all_ = AllowAllVersions

        v1 = ver("1.0.0")
        s1 = spec(f"=={v1}")

        assert_spec(all_.difference_from(s1), '!=1.0.0')
        assert_spec(all_.intersect_with(s1), '==1.0.0')
        assert_spec(all_.union_with(s1), '*')

        r1 = spec(f">{v1},<2.0.0")
        # r1 = StandardVersionRange.create(cast(StandardVersion, v1), StandardVersion((2, 0, 0)))
        assert_spec(all_.difference_from(r1), '<=1.0.0; >=2.0.0')

        assert_spec(all_.inverse().inverse(), '*')

    def test_ordering(self):
        assert spec(">=4.62,<4.65") < spec(">=4.62")


def assert_spec(version: VersionSpecifier, expected_str: str) -> None:
    vstr = str(version)  # noqa
    assert vstr == expected_str, \
        f"unexpected version: '{vstr}' was expected to be '{expected_str}'"
