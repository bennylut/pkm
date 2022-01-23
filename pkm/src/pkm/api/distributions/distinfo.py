import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, ClassVar, Iterable, Dict

from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.versions.version import Version, StandardVersion
from pkm.config.configuration import IniFileConfiguration, FileConfiguration, computed_based_on
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.hashes import HashSignature
from pkm.utils.iterators import groupby


class DistInfo:

    def __init__(self, path: Path):
        self.path = path

    def load_wheel_cfg(self) -> "WheelFileConfiguration":
        return WheelFileConfiguration.load(self.wheel_path())

    def wheel_path(self) -> Path:
        return self.path / "WHEEL"

    def load_entrypoints_cfg(self) -> "EntrypointsConfiguration":
        return EntrypointsConfiguration.load(self.path / "entry_points.txt")

    def load_metadata_cfg(self) -> "PackageMetadata":
        return PackageMetadata.load(self.metadata_path())

    def metadata_path(self) -> Path:
        return self.path / "METADATA"

    def load_record_cfg(self) -> "RecordsFileConfiguration":
        return RecordsFileConfiguration.load(self.record_path())

    def record_path(self) -> Path:
        return self.path / "RECORD"

    def license_path(self) -> Path:
        return self.path / "LICENSE"

    @classmethod
    def load(cls, path: Path) -> "DistInfo":
        if path.suffix != '.dist-info':
            raise UnsupportedOperationException("not a dist-info directory")

        return cls(path)


class EntrypointsConfiguration(IniFileConfiguration):
    entrypoints: List["EntryPoint"]

    @computed_based_on("")
    def entrypoints(self) -> Iterable["EntryPoint"]:

        result: List[EntryPoint] = []

        for group_name, group in self.items():
            for entry_point, object_ref in group.items():
                result.append(EntryPoint(group_name, entry_point, ObjectReference.parse(object_ref)))

        return result

    @entrypoints.modifier
    def set_entrypoints(self, entries: List["EntryPoint"]):
        self._data.clear()
        by_group: Dict[str, List[EntryPoint]] = groupby(entries, key=lambda e: e.group)
        new_data = {group: {e.name: e.ref for e in entries} for group, entries in by_group.items()}
        self._data.update(new_data)


@dataclass
class EntryPoint:
    group: str
    name: str
    ref: "ObjectReference"

    G_CONSOLE_SCRIPTS: ClassVar[str] = "console_scripts"
    G_GUI_SCRIPTS: ClassVar[str] = "gui_scripts"

    def is_script(self) -> bool:
        """
        :return: true if this entrypoint belongs to one of the script groups, false otherwise
        """

        return self.group in (EntryPoint.G_CONSOLE_SCRIPTS, EntryPoint.G_GUI_SCRIPTS)


# noinspection RegExpRedundantEscape
_OBJ_REF_RX = re.compile(r"(?P<mdl>[^:]*)(:(?P<obj>[^\[]*)\s*(\[\s*(?P<ext>[^\]]*)\s*\])?)?")
_EXT_DELIM_RX = re.compile("\\s*,\\s*")


@dataclass(frozen=True)
class ObjectReference:
    module_path: str
    object_path: Optional[str] = None
    extras: Optional[List[str]] = None

    def __str__(self):
        obj_str = f":{self.object_path}" if self.object_path else ""
        ext_str = f" [{', '.join(self.extras)}]" if self.extras else ""
        return f"{self.module_path}{obj_str}{ext_str}"

    def execution_script_snippet(self) -> str:
        if not self.object_path:
            raise UnsupportedOperationException(
                f"{str(self)} cannot be used as script generator - "
                f"it must be of the format module.path:zero.arg.function.path")

        return f"import sys;import {self.module_path};sys.exit({self.module_path}.{self.object_path}())"

    @classmethod
    def parse(cls, refstr: str) -> "ObjectReference":
        if not (match := _OBJ_REF_RX.match(refstr)):
            raise ValueError(f"could not parse object reference from string: '{refstr}'")

        module_path = match.group('mdl')
        object_path = match.group('obj')
        extras = _EXT_DELIM_RX.split(ext.strip()) if (ext := match.group('ext')) else None

        return ObjectReference(module_path, object_path, extras)


class WheelFileConfiguration(FileConfiguration):

    def generate_content(self) -> str:
        return os.linesep.join(f'{k}: {v}' for k, v in self._data.items())

    def validate_supported_version(self):
        wv = Version.parse(self['Wheel-Version'] or 'unprovided')
        if not isinstance(wv, StandardVersion):
            raise UnsupportedOperationException(f"unknown wheel version: {wv}")

        if wv.release[0] != 1:
            raise UnsupportedOperationException(f"unsupported wheel version: {wv}")
        if wv.release[1] != 0:
            print(f'advanced wheel version: {wv} detected, will be treated as version 1.0')

    @classmethod
    def create(cls, generator: str, purelib: bool):
        return cls(path=None, data={
            'Wheel-Version': '1.0',
            'Generator': generator,
            'Root-Is-Purelib': 'true' if purelib else 'false'
        })

    @classmethod
    def load(cls, path: Path):
        if not path.exists():
            raise UnsupportedOperationException(f"wheel does not contain WHEEL file in dist-info")

        seperator_rx = re.compile("\\s*:\\s*")
        lines = (line.strip() for line in path.read_text().splitlines())
        kvs = (seperator_rx.split(kv) for kv in lines if kv)
        return cls(path=path, data={kv[0]: kv[1] for kv in kvs})


@dataclass(frozen=True)
class Record:
    file: str
    hash_signature: HashSignature
    length: int


class RecordsFileConfiguration(FileConfiguration):

    def generate_content(self) -> str:
        raise UnsupportedOperationException()

    @property
    def records(self) -> List[Record]:
        return self['records']

    def save_to(self, path: Optional[Path] = None):
        path = path or self.path
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open('w+', newline='') as new_record_fd:
            r: Record
            csv.writer(new_record_fd).writerows(
                (str(r.file), str(r.hash_signature), r.length)
                for r in self['records'])

    def sign(self, content_root: Path):
        """
        add to the records in this file the signatures for files inside the `content_root`
        :param content_root: the content to sign
               (will recursively sign all files in the content root and add their signature to the created record file)
        """

        records: List[Record] = self.records
        for file in content_root.rglob("*"):
            if not file.is_dir():
                records.append(Record(
                    str(file.relative_to(content_root)),  # path
                    HashSignature.create_urlsafe_base64_nopad_encoded('sha256', file),  # signature
                    file.lstat().st_size  # size
                ))

    @classmethod
    def load(cls, path: Path) -> "RecordsFileConfiguration":
        records = []

        if path.exists():
            with path.open('r', newline='') as records_fd:
                for record in csv.reader(records_fd):
                    file, hash_sig, length = record
                    if hash_sig:
                        records.append(Record(
                            file,
                            HashSignature.parse_urlsafe_base64_nopad_encoded(hash_sig),
                            int(length),
                        ))

        return RecordsFileConfiguration(data={'records': records}, path=path)
