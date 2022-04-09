from __future__ import annotations

from abc import abstractmethod, ABC
from dataclasses import dataclass, replace
from typing import List, Optional

from pkm.api.versions.version import Version, StandardVersion, UrlVersion
from pkm.utils.iterators import distinct
from pkm.utils.sequences import subiter


class VersionSpecifier(ABC):
    """
    represents a version specifier (e.g., >=1.0.1)
    supported operators are: 
    comparison: >,>=,<,<=
    equality: ==, ===, !==, !===, ~=
    url matching: @ 
    """

    def specific_url(self) -> Optional[UrlVersion]:
        """
        :return: if the version specifier is a url matching specifier, returns its version, otherwise returns None  
        """
        return None

    def allows_all(self, other: "VersionSpecifier") -> bool:
        """
        :param other: 
        :return: True if this specifier allows all the versions that are allowed by `other`
        """
        return self.intersect(other) == other

    def allows_any(self, other: "VersionSpecifier") -> bool:
        """
        :param other: 
        :return: True if this specifier allows at least one of the versions that are allowed by `other` 
        """
        return not self.intersect(other).is_none()

    def allows_version(self, version: "Version"):
        """
        :param version: the version to check 
        :return: True if the given `version` is allowed by this version specifier, False otherwise
        """
        return any(segment.allows_version(version) for segment in self._segments())

    def allows_pre_or_dev_releases(self) -> bool:
        """
        :return: True if this specifier accepts version that are pre or dev releases, False otherwise 
        """
        return any(segment.allows_pre_or_dev_releases() for segment in self._segments())

    def intersect(self, other: "VersionSpecifier") -> "VersionSpecifier":
        """
        :param other: 
        :return: a new version specifier that accepts only versions 
                 that are accepted by both self and `other` 
        """
        return _intersect(self, other)

    def union(self, other: "VersionSpecifier") -> "VersionSpecifier":
        """
        :param other: 
        :return: a new version specifier that accepts any versions that are accepted
                 by either self or `other` 
        """
        result = _unite([*self._segments(), *other._segments()])
        return result

    def is_none(self):
        """
        :return: True if this version specifier does not accept any version, False otherwise 
        """
        return self.min == self.max and self.includes_min == self.includes_max == False  # noqa

    def is_any(self):
        """
        :return: True if this version specifier accepts all versions, False otherwise
        """
        return (self.min is self.max is None) and self.includes_min == self.includes_max == True  # noqa

    def _segments(self) -> List["VersionSpecifier"]:
        return [self]

    def difference(self, other: "VersionSpecifier") -> "VersionSpecifier":
        """
        :param other: 
        :return: a new version specifier that accepts any versions that are accepted
                 by self but not by `other` 
        """
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
    def min(self) -> Optional["Version"]:
        """
        :return: the minimal version that is accepted by this specifier (may-be exclusive)
        """
        return self._segments()[0].min

    @property
    def max(self) -> Optional["Version"]:
        """
        :return: the maximal version that is accepted by this specifier (may-be exclusive)
        """
        return self._segments()[-1].max

    @property
    def includes_min(self) -> bool:
        """
        :return: True if the value returned by `self.min` is inclusive
        """
        return self._segments()[0].includes_min

    @property
    def includes_max(self) -> bool:
        """
        :return: True if the value returned by `self.max` is inclusive
        """
        return self._segments()[1].includes_max

    @abstractmethod
    def inverse(self) -> "VersionSpecifier":
        """
        :return: a new version specifier that accepts any version that was not accepted by this specifier
        """

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

    def specific_url(self) -> Optional[UrlVersion]:
        if isinstance(self.version, UrlVersion):
            return self.version
        return None

    def allows_version(self, version: "Version"):
        if self.version.is_local():
            return version == self.version
        else:
            return version.without_local() == self.version

    def __str__(self):
        if isinstance(self.version, StandardVersion):
            return f'=={self.version}'
        elif isinstance(self.version, UrlVersion):
            return f'@{self.version}'
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
            if other.min == self.version:
                return replace(other, includes_min=True)
            elif other.max == self.version:
                return replace(other, includes_max=True)
            elif (other.min is None or other.min < self.version) and (other.max is None or self.version < other.max):
                return other
            return None

        assert False, f'merging only support non union versions, attempting to merge: {self} with {other}'
        return None  # noqa

    def inverse(self) -> "VersionSpecifier":
        return VersionUnion([
            VersionRange(max=self.version, includes_max=False),
            VersionRange(min=self.version, includes_min=False)
        ])

    @property
    def min(self) -> Optional["Version"]:
        return self.version

    @property
    def max(self) -> Optional["Version"]:
        return self.version

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
    min: Optional[Version] = None
    max: Optional[Version] = None
    includes_min: bool = None
    includes_max: bool = None

    def __post_init__(self):
        assert self.min is None or self.max is None or self.min <= self.max, f'min > max :: {self.min} > {self.max}'

        self.includes_max = self.includes_max if self.includes_max is not None else self.max is None
        self.includes_min = self.includes_min if self.includes_min is not None else self.min is None

    def allows_pre_or_dev_releases(self) -> bool:
        max_ = self.max
        return max_ is not None and max_.is_pre_or_dev_release()

    # note that pep440 pre-release filtering rules should be implemented in the repository and not here
    def allows_version(self, version: "Version"):

        if self.is_any():
            return not version.is_post_release()
        if self.is_none():
            return False

        min_, max_ = self.min, self.max
        if (min_ is not None and self.includes_min and min_ == version) \
                or (max_ is not None and self.includes_max and max_ == version):
            return True

        if version.is_post_release() and (min_ is None or not min_.is_post_release()):
            return False

        return (min_ is None or min_ < version) and (max_ is None or version < max_)

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

        return _unite(new_segments)

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
            res += str(self.min)

        if self.max is not None:
            if res:
                res += ', '
            res += '<'
            if self.includes_max:
                res += '='
            res += str(self.max)

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
        self.unions: List[VersionSpecifier] = constraints  # assumed to be ordered..

    def inverse(self) -> "VersionSpecifier":
        result = self.unions[0].inverse()
        for c in subiter(self.unions, 1):
            if result.is_none():
                return result

            result = result.intersect(c.inverse())
        return result

    def _try_merge(self, other: "VersionSpecifier") -> Optional["VersionSpecifier"]:
        assert False, 'merging only support non union versions'
        return None  # noqa

    def __str__(self):
        if len(self.unions) == 2:
            a, b = self.unions
            if a.min is None and b.max is None and a.max == b.min and (a.includes_max is b.includes_min is False):
                return f"!={a.max}"

        return '; '.join(str(it) for it in self.unions)

    def _segments(self) -> List["VersionSpecifier"]:
        return self.unions


NoVersion = VersionRange(includes_min=False, includes_max=False)
AnyVersion = VersionRange(includes_min=True, includes_max=True)


# UTILS

def _unite(segments: List["VersionSpecifier"]) -> "VersionSpecifier":
    if not segments:
        return NoVersion

    segments = sorted(segments)
    new_segments: List[VersionSpecifier] = []

    last: VersionSpecifier = segments[0]
    for segment in subiter(segments, 1):
        joined = last._try_merge(segment)  # noqa
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


def _intersect(a: VersionSpecifier, b: VersionSpecifier) -> "VersionSpecifier":
    swap = False

    if isinstance(a, VersionUnion) or (swap := isinstance(b, VersionUnion)):
        if swap: a, b = b, a  # noqa

        b_segments = [b]
        if isinstance(b, VersionUnion):
            b_segments = b.unions

        return _unite([
            intersection
            for it in a.unions
            for segment in b_segments
            if not (intersection := _intersect(it, segment)).is_none()])

    if isinstance(a, SpecificVersion) or (swap := isinstance(b, SpecificVersion)):
        if swap: a, b = b, a  # noqa

        if isinstance(b, SpecificVersion):
            if a.version == b.version:
                return a
            elif (a.version.is_local() or (swap := b.version.is_local())) \
                    and a.version.without_local() == b.version.without_local():
                return b if swap else a

            return NoVersion

        if isinstance(b, VersionRange):
            if b.is_any() or b.allows_version(a.version.without_local()):
                return a
            return NoVersion

        raise ValueError(f"unexpected version specifier type: {b}")

    # both a and b are version ranges
    if a.is_none() or (swap := b.is_none()):
        return b if swap else a
    if a.is_any() or (swap := b.is_any()):
        return a if swap else b

    min1, min2 = a.min, b.min
    selected_min = min1
    if min1 == min2:
        includes_min = a.includes_min and b.includes_min
    else:
        includes_min = a.includes_min
        if min1 is None or (min2 is not None and min2 > min1):
            selected_min = min2
            includes_min = b.includes_min

    max1, max2 = a.max, b.max
    selected_max = max1
    if max1 == max2:
        includes_max = a.includes_max and b.includes_max
    else:
        includes_max = a.includes_max
        if max1 is None or (max2 is not None and max2 < max1):
            selected_max = max2
            includes_max = b.includes_max

    if includes_max and includes_min and selected_max == selected_min:
        return SpecificVersion(selected_min)
    elif selected_min is None or selected_max is None or selected_min < selected_max:
        return VersionRange(
            min=selected_min, max=selected_max, includes_min=includes_min, includes_max=includes_max)

    return NoVersion
