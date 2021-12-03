from typing import Tuple, Optional

from dataclasses import dataclass, replace
from typing_extensions import Literal

from pkm.utils.sequences import startswith


@dataclass(frozen=True, repr=False)
class Version:
    release: Tuple[int, ...]
    epoch: Optional[int] = None
    pre_release: Optional[Tuple[Literal['a', 'b', 'rc'], int]] = None
    post_release: Optional[int] = None
    dev_release: Optional[int] = None
    local_label: Optional[str] = None

    # def is_pre_release(self) -> bool:
    #     return self.pre_release is not None

    def is_pre_or_dev_release(self) -> bool:
        return self.pre_release is not None or self.dev_release is not None

    def is_post_release(self) -> bool:
        return self.post_release is not None

    def is_local(self) -> bool:
        return self.local_label is not None

    def __str__(self):
        vstring = ''
        if self.epoch is not None:
            vstring += f'{self.epoch}!'
        vstring += '.'.join(str(n) for n in self.release)
        if self.pre_release is not None:
            vstring += ''.join(str(it) for it in self.pre_release)
        if self.post_release is not None:
            vstring += f'.post{self.post_release}'
        if self.dev_release is not None:
            vstring += f'.dev{self.dev_release}'
        if self.local_label is not None:
            vstring += f'+{self.local_label}'

        return vstring

    def __repr__(self):
        return str(self)

    def __lt__(self, other: "Version"):
        if (self.epoch or 0) != (other.epoch or 0):
            return (self.epoch or 0) < (other.epoch or 0)

        v1, v2 = Version.normalized(self, other)
        for s, o in zip(v1.release, v2.release):
            if s == o: continue
            return s < o

        if self.dev_release != other.dev_release:
            if (self.dev_release is None) ^ (other.dev_release is None):
                return other.dev_release is None

            if self.dev_release != other.dev_release:
                return self.dev_release < other.dev_release

        if self.pre_release != other.pre_release:
            if (self.pre_release is None) ^ (other.pre_release is None):
                return other.pre_release is None

            for s, o in zip(self.pre_release, other.pre_release):
                if s == o: continue  # noqa
                return s < o

        if self.post_release != other.post_release:
            if (self.post_release is None) ^ (other.post_release is None):
                return self.post_release is None

            s, o = self.post_release, other.post_release
            if s != o:
                return s < o

        my_local_segments = (self.local_label or "").split('.')
        other_local_segments = (other.local_label or "").split('.')

        for m, o in zip(my_local_segments, other_local_segments):
            if m == o:
                continue

            m_num, o_num = m.isnumeric(), o.isnumeric()
            if m_num and o_num:
                return int(m_num) < int(o_num)
            if m_num or o_num:
                return o_num

            return m < o

        return len(my_local_segments) < len(other_local_segments)

    def __eq__(self, other):
        if not isinstance(other, Version):
            return False

        v1, v2 = Version.normalized(self, other)
        return (v1.epoch or 0) == (other.epoch or 0) \
               and v1.release == v2.release \
               and v1.pre_release == v2.pre_release \
               and v1.post_release == v2.post_release \
               and v1.dev_release == v2.dev_release \
               and v1.local_label == v2.local_label  # noqa

    @staticmethod
    def normalized(v1: "Version", v2: "Version") -> Tuple["Version", "Version"]:
        v1rel, v2rel = v1.release, v2.release  # noqa
        rlen = max(len(v1rel), len(v2rel))  # noqa

        if len(v1rel) != rlen:
            v1rel += (0,) * (rlen - len(v1rel))
        if len(v2rel) != rlen:
            v2rel += (0,) * (rlen - len(v2rel))

        return ((v1 if v1rel == v1.release else replace(v1, release=v1rel)),
                (v2 if v2rel == v2.release else replace(v2, release=v2rel)))

    @classmethod
    def parse(cls, txt: str) -> "Version":
        from pkm_main.versions.version_parser import version_parser
        return version_parser.parse_version(txt)
