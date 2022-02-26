from __future__ import annotations
import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Iterable, Dict, Iterator

from pkm.api.packages.package_metadata import PackageMetadata
from pkm.api.versions.version import Version, StandardVersion
from pkm.config.configuration import IniFileConfiguration, FileConfiguration, computed_based_on
from pkm.utils.commons import UnsupportedOperationException
from pkm.utils.entrypoints import EntryPoint, ObjectReference
from pkm.utils.files import path_to, resolve_relativity
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
        return cls(path)

    def installed_files(self) -> Iterator[Path]:
        """
        :return: paths to all the files that were installed to the environment via this package (taken from RECORD)
        """
        root = self.path.parent
        for record in self.load_record_cfg().records:
            file = resolve_relativity(Path(record.file), root).resolve()
            yield file

        yield self.record_path()


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

    def sign_files(self, files: Iterable[Path], root: Path) -> RecordsFileConfiguration:
        """
        add to the records in this file the signatures for the given `files`
        :param files: the files to sign
        :param root: a root directory to sign the files relative to, when signing, the record file path will be writen
                     relative to this root
        :return: self (for chaining support)
        """
        records: List[Record] = self.records
        for file in files:
            if not file.is_dir():
                records.append(Record(
                    str(path_to(root, file)),  # path
                    HashSignature.create_urlsafe_base64_nopad_encoded('sha256', file),  # signature
                    file.lstat().st_size  # size
                ))

        return self

    def sign_recursive(self, content_root: Path) -> RecordsFileConfiguration:
        """
        add to the records in this file the signatures for files inside the `content_root`
        :param content_root: the content to sign
               (will recursively sign all files in the content root and add their signature to the created record file)
        :return: self (for chaining support)
        """
        return self.sign_files(content_root.rglob("*"), content_root)

    @classmethod
    def load(cls, path: Path) -> "RecordsFileConfiguration":
        records = []

        if path.exists():
            with path.open('r', newline='') as records_fd:
                for record in csv.reader(records_fd):
                    file, hash_sig, length = record
                    if hash_sig:
                        records.append(Record(
                            str(Path(file)),  # wrapping in path and then str so that os dependent path will be used
                            HashSignature.parse_urlsafe_base64_nopad_encoded(hash_sig),
                            int(length),
                        ))

        return RecordsFileConfiguration(data={'records': records}, path=path)
