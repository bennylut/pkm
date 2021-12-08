from typing import List

from dataclasses import replace
from pkm.utils.parsing import SimpleParser
from pkm.api.versions.version import Version
from pkm.api.versions.version_specifiers import VersionSpecifier, VersionRange, SpecificVersion, AnyVersion, \
    ExactVersionString


def parse_version(version_str: str) -> Version:
    return VersionParser(version_str.lower()).read_version()


def parse_specifier(specifier_str: str) -> VersionSpecifier:
    return VersionParser(specifier_str.lower()).read_specifier()


_PRE_RELEASE_TYPE_NORMALIZER = {
    'a': 'a', 'b': 'b', 'rc': 'rc', 'c': 'rc', 'alpha': 'a', 'beta': 'b', 'preview': 'rc'
}


class VersionParser(SimpleParser):

    def read_version(self) -> Version:
        self.read_ws()

        self.match('v')

        epoch = None
        n = self.read_digits()
        if self.match('!'):
            epoch = int(n)
            n = self.read_digits()

        release: List[int] = [int(n)]
        while self.match('.') and self.is_not_empty() and self.peek().isdigit():
            release.append(int(self.read_digits()))

        pre_release = None
        # pre_release_type = self.peek_prev() != '.' and self.match_any(*_PRE_RELEASE_TYPE_NORMALIZER.keys())
        pre_release_type = self.match_any(*_PRE_RELEASE_TYPE_NORMALIZER.keys())
        if pre_release_type:
            pre_release_num = 0 if not self.peek().isdigit() else int(self.read_digits())
            pre_release = (_PRE_RELEASE_TYPE_NORMALIZER[pre_release_type], pre_release_num)

        post_release = None

        if self.peek_prev().isdigit():
            self.match_any('.', '-', '_')
        if self.match_any('post', 'r', 'rev') or (self.peek_prev() == '-' and self.peek().isdigit()):
            self.match('-')
            post_release = 0 if not self.peek().isdigit() else int(self.read_digits())

        dev_release = None
        if self.peek_prev().isdigit():
            self.match_any('.', '-', '_')
        if self.match('dev'):
            dev_release = 0 if not self.peek().isdigit() else int(self.read_digits())

        local_label = None
        if self.match('+'):
            local_label = self.until(lambda i, s: s[i] not in ".-_" and not s[i].isalnum())
            local_label = local_label.translate(local_label.maketrans('-_', '..'))

        if self.peek_prev() == '.':
            self.position -= 1

        self.read_ws()

        return Version(release=tuple(release), epoch=epoch, pre_release=pre_release, post_release=post_release,
                       dev_release=dev_release, local_label=local_label)

    def _read_single_specifier(self) -> VersionSpecifier:
        self.read_ws()

        if self.match('*'):
            return AnyVersion

        if self.match('==='):
            self.read_ws()
            version_str = self.until(lambda i, t: t[i].isspace() or t[i] == ',')
            return ExactVersionString(version_str)

        exclusion_inclusion = self.match_any('==', '!=')
        if exclusion_inclusion:
            self.read_ws()
            version = self.read_version()
            if self.match('.*'):
                result = VersionRange(
                    min=SpecificVersion(version), includes_min=True,
                    max=SpecificVersion(
                        replace(version, release=version.release[:-1] + (version.release[-1] + 1,),
                                pre_release=None, post_release=None, dev_release=None, local_label=None)),
                    includes_max=False)
            else:
                result = SpecificVersion(version)

            if exclusion_inclusion == '!=':
                return result.inverse()
            return result

        if self.match('~='):
            self.read_ws()
            version = self.read_version()

            if len(version.release) == 1:
                raise ValueError(f"Illegal version specifier, ~= {version}")

            return VersionRange(
                min=SpecificVersion(version), includes_min=True,
                max=SpecificVersion(
                    replace(version, release=version.release[:-2] + (version.release[-2] + 1, 0),
                            pre_release=None, post_release=None, dev_release=None, local_label=None)),
                includes_max=False)

        comparison = self.match_any('>=', '>', '<=', '<')
        if comparison:
            self.read_ws()
            version = SpecificVersion(self.read_version())
            min, max, imin, imax = None, None, False, False

            if comparison[0] == '>':
                min, imin = version, len(comparison) > 1
            else:
                max, imax = version, len(comparison) > 1

            return VersionRange(min=min, max=max, includes_min=imin, includes_max=imax)

        self.raise_err('unknown operator')

    def read_specifier(self):
        self.read_ws()
        paren = self.match('(')

        specifier = AnyVersion
        while self.is_not_empty():
            specifier = specifier.intersect(self._read_single_specifier())
            self.read_ws()
            if not self.match(',') and self.is_not_empty():
                if paren and self.match(')'):
                    break

                self.raise_err('could not parse token')

        return specifier
