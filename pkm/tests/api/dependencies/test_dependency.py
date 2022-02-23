from unittest import TestCase

from pkm.api.dependencies.dependency import Dependency
from pkm.api.versions.version_specifiers import VersionSpecifier, AnyVersion


class TestDependency(TestCase):

    def test_parsing(self):
        assert_parsed("A", package_name="a")
        assert_parsed("A.B-C_D", package_name="a.b-c_d")
        assert_parsed("aa", package_name="aa")
        assert_parsed("name", package_name="name")
        assert_parsed("name<=1", package_name="name", version_spec=VersionSpecifier.parse("<=1"))
        assert_parsed("name>=3", package_name="name", version_spec=VersionSpecifier.parse(">=3"))
        assert_parsed("name>=3,<2", package_name="name", version_spec=VersionSpecifier.parse(">=3,<2"))
        assert_parsed("name@http://foo.com", package_name="name", url="http://foo.com")

        assert_parsed("name [fred,bar] @ http://foo.com ; python_version=='2.7'",
                      package_name="name", extras=["fred", "bar"], url="http://foo.com",
                      env_marker="python_version=='2.7'")

        assert_parsed("name[quux, strange];python_version<'2.7' and platform_version=='2'",
                      package_name="name", extras=["quux", "strange"], version_spec=AnyVersion,
                      env_marker="python_version<'2.7' and platform_version=='2'")

        assert_parsed("name; os_name=='a' or os_name=='b'",
                      package_name="name", version_spec=AnyVersion,
                      env_marker="os_name=='a' or os_name=='b'")

        assert_parsed("name; os_name=='a' and os_name=='b' or os_name=='c'",
                      package_name="name", version_spec=AnyVersion,
                      env_marker="os_name=='a' and os_name=='b' or os_name=='c'")

        assert_parsed("name; os_name=='a' and (os_name=='b' or os_name=='c')",
                      package_name="name", version_spec=AnyVersion,
                      env_marker="os_name=='a' and (os_name=='b' or os_name=='c')")

        assert_parsed("name; os_name=='a' or os_name=='b' and os_name=='c'",
                      package_name="name", version_spec=AnyVersion,
                      env_marker="os_name=='a' or os_name=='b' and os_name=='c'")

        assert_parsed("name; (os_name=='a' or os_name=='b') and os_name=='c'",
                      package_name="name", version_spec=AnyVersion,
                      env_marker="(os_name=='a' or os_name=='b') and os_name=='c'")

        assert_parsed('pyOpenSSL>=0.14; python_version<="2.7" and extra == \'secure\'',
                      package_name="pyopenssl", version_spec=VersionSpecifier.parse(">=0.14"),
                      env_marker="python_version<=\"2.7\" and extra == \'secure\'")

        assert_parsed('botocore (<2.0a.0,>=1.12.36)', package_name='botocore',
                      version_spec=VersionSpecifier.parse("<2.0a.0,>=1.12.36"))

        assert_parsed('pip (<20.3.*,>=20.1.*)', package_name='pip', version_spec=VersionSpecifier.parse('<20.3,>=20.1'))


def assert_parsed(text: str, **kwargs):
    assert_dependency(Dependency.parse(text), **kwargs)


def assert_dependency(d: Dependency, **kwargs):
    for key, value in kwargs.items():
        if key == 'env_marker':
            assert str(d.env_marker) == value, f"expecting env-marker to be {value} but it was {d.env_marker}"
        elif key == 'url':
            assert (url := d.version_spec.specific_url()), f"expecting url dependency but got non-url one"
            assert str(url) == value, f"expecting url dependency to have the url: " \
                                      f"{value} but it was {url}"
        else:
            assert getattr(d, key) == value, f"expecting {key} to be {value} but it was {getattr(d, key)}"
