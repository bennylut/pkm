from abc import abstractmethod, ABC
from dataclasses import dataclass, replace
from typing import List, Optional

from pkm.api.versions.version import Version, StandardVersion
from pkm.utils.iterators import distinct
from pkm.utils.sequences import subiter


class VersionSpecifier(ABC):

    def allows_all(self, other: "VersionSpecifier") -> bool:
        return self.intersect(other) == other

    def allows_any(self, other: "VersionSpecifier") -> bool:
        return not self.intersect(other).is_none()

    def allows_version(self, version: "Version"):
        return any(segment.allows_version(version) for segment in self._segments())

    def allows_pre_or_dev_releases(self) -> bool:
        return any(segment.allows_pre_or_dev_releases() for segment in self._segments())

    def intersect(self, other: "VersionSpecifier") -> "VersionSpecifier":

        def no_local(v: Optional[SpecificVersion]):
            if v is None:
                return None
            return v.version.without_local()

        new_segments: List[VersionSpecifier] = []
        for s1 in self._segments():
            if s1.is_none(): continue  # noqa
            if s1.is_any(): return other  # noqa

            for s2 in other._segments():
                if s2.is_none(): continue  # noqa
                if s2.is_any(): return self  # noqa

                min1, min2 = s1.min, s2.min
                selected_min = min1

                if no_local(min1) == no_local(min2):
                    includes_min = s1.includes_min and s2.includes_min
                    if min2 and min2.version.is_local():
                        selected_min = min2
                else:
                    includes_min = s1.includes_min
                    if min1 is None or (min2 is not None and min2 > min1):
                        selected_min = min2
                        includes_min = s2.includes_min

                max1, max2 = s1.max, s2.max
                selected_max = max1

                if no_local(max1) == no_local(max2):
                    includes_max = s1.includes_max and s2.includes_max
                    if max2 and max2.version.is_local():
                        selected_max = max2
                else:
                    includes_max = s1.includes_max

                    if max1 is None or (max2 is not None and max2 < max1):
                        selected_max = max2
                        includes_max = s2.includes_max

                if includes_max and includes_min and selected_max == selected_min:
                    new_segments.append(selected_min)
                elif selected_min is None or selected_max is None or selected_min < selected_max:
                    new_segments.append(VersionRange(
                        min=selected_min, max=selected_max, includes_min=includes_min, includes_max=includes_max))

        return VersionSpecifier._unite(new_segments)

    @staticmethod
    def _unite(segments: List["VersionSpecifier"]) -> "VersionSpecifier":

        if not segments:
            return NoVersion

        segments = sorted(segments)
        new_segments: List[VersionSpecifier] = []

        last: VersionSpecifier = segments[0]
        for segment in subiter(segments, 1):
            joined = last._try_merge(segment)
            if joined:
                last = joined
            else:
                new_segments.append(last)
                last = segment
        new_segments.append(last)

        new_segments = list(distinct(new_segments))

        if not new_segments:
            return NoVersion
        elif len(new_segments) == 1:
            return new_segments[0]

        return VersionUnion(new_segments)

    def union(self, other: "VersionSpecifier") -> "VersionSpecifier":
        return VersionSpecifier._unite([*self._segments(), *other._segments()])

    def is_none(self):
        return self.min == self.max and self.includes_min == self.includes_max == False  # noqa

    def is_any(self):
        return (self.min is self.max is None) and self.includes_min == self.includes_max == True  # noqa

    def _segments(self) -> List["VersionSpecifier"]:
        return [self]

    def difference(self, other: "VersionSpecifier") -> "VersionSpecifier":
        return self.intersect(other.inverse())

    def __lt__(self, other: "VersionSpecifier") -> bool:
        smin, omin = self.min, other.min  # noqa

        if smin == omin:
            if self.includes_min == other.includes_min:
                smax, omax = self.max, other.max

                if smax == omax:
                    if self.includes_max == other.includes_max:
                        return str(self) < str(other)
                    return other.includes_max
                # return Version.less(smax, omax)
                return omax is None or (smax is not None and smax < omax)
            return self.includes_min

        return smin is None or (omin is not None and smin < omin)

    def __le__(self, other: "VersionSpecifier"):
        return other == self or self < other

    @property
    def min(self) -> Optional["SpecificVersion"]:
        return self._segments()[0].min

    @property
    def max(self) -> Optional["SpecificVersion"]:
        return self._segments()[-1].max

    @property
    def includes_min(self) -> bool:
        return self._segments()[0].includes_min

    @property
    def includes_max(self) -> bool:
        return self._segments()[1].includes_max

    @abstractmethod
    def inverse(self) -> "VersionSpecifier":
        ...

    @abstractmethod
    def _try_merge(self, other: "VersionSpecifier") -> Optional["VersionSpecifier"]:
        ...

    def __repr__(self):
        return str(self)

    @classmethod
    def parse(cls, txt: str) -> "VersionSpecifier":
        from pkm.api.versions.version_parser import parse_specifier
        return parse_specifier(txt)


@dataclass(frozen=True)
class SpecificVersion(VersionSpecifier):
    version: Version

    def allows_version(self, version: "Version"):
        if self.version.is_local():
            return version == self.version
        else:
            return version.without_local() == self.version

    def __str__(self):
        if isinstance(self.version, StandardVersion):
            return f'=={self.version}'
        return f"==={self.version}"

    def __repr__(self):
        return str(self)

    def allows_pre_or_dev_releases(self) -> bool:
        return self.version.is_pre_or_dev_release()

    def _try_merge(self, other: "VersionSpecifier") -> Optional["VersionSpecifier"]:
        if other == self:
            return other
        if isinstance(other, SpecificVersion):
            return None
        if isinstance(other, VersionRange):
            if other.min == self:
                return replace(other, includes_min=True)
            elif other.max == self:
                return replace(other, includes_max=True)
            elif (other.min is None or other.min < self) and (other.max is None or self < other.max):
                return other
            return None

        assert False, 'merging only support non union versions'
        return None  # noqa

    def inverse(self) -> "VersionSpecifier":
        return VersionUnion([
            VersionRange(max=self, includes_max=False),
            VersionRange(min=self, includes_min=False)
        ])

    @property
    def min(self) -> Optional["SpecificVersion"]:
        return self

    @property
    def max(self) -> Optional["SpecificVersion"]:
        return self

    @property
    def includes_min(self) -> bool:
        return True

    @property
    def includes_max(self) -> bool:
        return True

    def __lt__(self, other: "VersionSpecifier"):
        if not isinstance(other, SpecificVersion):
            return super().__lt__(other)

        return self.version < other.version


@dataclass(unsafe_hash=True, repr=False)
class VersionRange(VersionSpecifier):
    min: Optional["SpecificVersion"] = None
    max: Optional["SpecificVersion"] = None
    includes_min: bool = None
    includes_max: bool = None

    def __post_init__(self):
        assert self.min is None or self.max is None or self.min <= self.max, f'min > max :: {self.min} > {self.max}'

        self.includes_max = self.includes_max if self.includes_max is not None else self.max is None
        self.includes_min = self.includes_min if self.includes_min is not None else self.min is None

    def allows_pre_or_dev_releases(self) -> bool:
        max_ = self.max
        return max_ is not None and max_.version.is_pre_or_dev_release()

    # note that pep440 pre-release filtering rules should be implemented in the repository and not here
    def allows_version(self, version: "Version"):

        # if version.is_local():
        #     return False

        if self.is_any():
            # return not version.is_pre_or_dev_release() and not version.is_post_release()
            return not version.is_post_release()
        if self.is_none():
            return False

        min_, max_ = self.min, self.max
        if (min_ is not None and self.includes_min and min_.version == version) \
                or (max_ is not None and self.includes_max and max_.version == version):
            return True

        if version.is_post_release() and (min_ is None or not min_.version.is_post_release()):
            return False

        # if version.is_pre_or_dev_release() and (max is None or not max.version.is_pre_or_dev_release()):
        #     return False

        return (min_ is None or min_.version < version) and (max_ is None or version < max_.version)

    def inverse(self) -> "VersionSpecifier":
        new_segments: List["VersionSpecifier"] = []

        if self.is_any():
            return NoVersion
        if self.is_none():
            return AnyVersion

        if self.min is not None:
            new_segments.append(VersionRange(max=self.min, includes_max=not self.includes_min))
        if self.max is not None:
            new_segments.append(VersionRange(min=self.max, includes_min=not self.includes_max))

        return VersionSpecifier._unite(new_segments)

    def __str__(self):

        if self.is_any():
            return ''
        elif self.is_none():
            return '<none>'

        res = ''
        if self.min is not None:
            res += '>'
            if self.includes_min:
                res += '='
            res += str(self.min.version)

        if self.max is not None:
            if res:
                res += ', '
            res += '<'
            if self.includes_max:
                res += '='
            res += str(self.max.version)

        return res

    def _try_merge(self, other: VersionSpecifier) -> Optional[VersionSpecifier]:
        if isinstance(other, SpecificVersion):
            return other._try_merge(self)  # noqa

        min1, min2 = self.min, other.min
        if min2 is not None and (min1 is None or min1 < min2):
            sprv, snxt = self, other
        else:
            sprv, snxt = other, self

        if snxt.min is None or sprv.max is None or snxt.min < sprv.max or \
                (snxt.min == sprv.max and (sprv.includes_max or snxt.includes_min)):
            return VersionRange(min=sprv.min, max=snxt.max, includes_min=sprv.includes_min,
                                includes_max=snxt.includes_max)

        return None


class VersionUnion(VersionSpecifier):
    def __init__(self, constraints: List[VersionSpecifier]):
        self._constraints: List[VersionSpecifier] = constraints  # assumed to be ordered..

    def inverse(self) -> "VersionSpecifier":
        result = self._constraints[0].inverse()
        for c in subiter(self._constraints, 1):
            if result.is_none():
                return result

            result = result.intersect(c.inverse())

        return result

    def _try_merge(self, other: "VersionSpecifier") -> Optional["VersionSpecifier"]:
        assert False, 'merging only support non union versions'
        return None  # noqa

    def __str__(self):
        if len(self._constraints) == 2:
            a, b = self._constraints
            if a.min is None and b.max is None and a.max == b.min and (a.includes_max is b.includes_min is False):
                return f"!={a.max.version}"

        return '; '.join(str(it) for it in self._constraints)

    def _segments(self) -> List["VersionSpecifier"]:
        return self._constraints


NoVersion = VersionRange(includes_min=False, includes_max=False)
AnyVersion = VersionRange(includes_min=True, includes_max=True)
