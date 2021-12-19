from pathlib import Path
from typing import Dict
from unittest import TestCase

from pkm.api.dependencies.env_markers import EnvironmentMarker
from pkm.api.environments.environment import UninitializedEnvironment


class TestEnvMarkers(TestCase):

    def test_sanity(self):
        assert_with_env("python_version=='2.7'", True, python_version="2.7")
        assert_with_env("python_version=='2.7'", True, python_version="2.7.0")
        assert_with_env("python_version=='2.7'", False, python_version="2.7.1")
        assert_with_env("python_version=='2.7'", False, python_version="3.0.0")

        assert_with_env("python_version<'2.7' and platform_version=='2'", False,
                        python_version="2.1", platform_version="3")
        assert_with_env("python_version<'2.7' and platform_version=='2'", False, python_version="2.8",
                        platform_version="2")
        assert_with_env("python_version<'2.7' and platform_version=='2'", True, python_version="2.1",
                        platform_version="2")

        assert_with_env("os_name=='a' or os_name=='b'", True, os_name="a")
        assert_with_env("os_name=='a' or os_name=='b'", True, os_name="b")
        assert_with_env("os_name=='a' or os_name=='b'", False, os_name="c")

        # Should parse as (a and b) or c
        assert_with_env("os_name=='a' and os_name=='b' or os_name=='c'", False, os_name="a")
        assert_with_env("os_name=='a' and os_name=='b' or os_name=='c'", False, os_name="b")
        assert_with_env("os_name=='a' and os_name=='b' or os_name=='c'", True, os_name="c")

        # Overriding precedence -> a and (b or c)
        assert_with_env("os_name=='a' and (os_name=='b' or os_name=='c')", False, os_name="a")
        assert_with_env("os_name=='a' and (os_name=='b' or os_name=='c')", False, os_name="b")
        assert_with_env("os_name=='a' and (os_name=='b' or os_name=='c')", False, os_name="c")

        # should parse as a or (b and c)
        assert_with_env("os_name=='a' or os_name=='b' and os_name=='c'", True, os_name="a")
        assert_with_env("os_name=='a' or os_name=='b' and os_name=='c'", False, os_name="b")
        assert_with_env("os_name=='a' or os_name=='b' and os_name=='c'", False, os_name="c")

        # Overriding precedence -> (a or b) and c
        assert_with_env("(os_name=='a' or os_name=='b') and os_name=='c'", False, os_name="a")
        assert_with_env("(os_name=='a' or os_name=='b') and os_name=='c'", False, os_name="b")
        assert_with_env("(os_name=='a' or os_name=='b') and os_name=='c'", False, os_name="c")

    def test_usage_of_extras(self):
        assert_with_env("extra == 'bam'", True, extras=['bam'])
        assert_with_env("extra == 'bam'", True, extras=['ba', 'bam'])
        assert_with_env("extra == 'bam'", False, extras=['ba', 'm'])


def assert_with_env(marker: str, expected: bool, **env_markers):
    parsed_marker = EnvironmentMarker.parse_pep508(marker)

    extras = env_markers.pop('extras', [])
    env = _MockEnvironment(env_markers)

    assert parsed_marker.evaluate_on(env, extras) == expected, \
        f"expecting {marker} to be evaluated to {expected} for env: {env_markers}, but it was not"


class _MockEnvironment(UninitializedEnvironment):

    def __init__(self, markers: Dict[str, str]):
        super().__init__(Path("."))
        self._markers = markers

    @property
    def markers(self) -> Dict[str, str]:
        return self._markers
