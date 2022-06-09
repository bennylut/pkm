import configparser
import csv
import json
import os
import re
from pathlib import Path
from typing import Mapping, Type, Any

from pkm.config import toml
from pkm.config.configclass import ConfigIO, _RAW_CONFIG_T, ConfigCodec, ConfigFieldCodec, _T, StringableFieldCodec


class TomlConfigIO(ConfigIO):
    def write(self, path: Path, data: _RAW_CONFIG_T):
        dumps = toml.dumps
        if path.exists():
            _, dumps = toml.load(path)

        path.write_text(dumps(data))

    def read(self, path: Path) -> _RAW_CONFIG_T:
        data, _ = toml.load(path)
        return data


class JsonConfigIO(ConfigIO):

    def write(self, path: Path, data: _RAW_CONFIG_T):
        with path.open("w") as fd:
            json.dump(data, fd)

    def read(self, path: Path) -> _RAW_CONFIG_T:
        with path.open("r") as fd:
            return json.load(fd)


class _CaseSensitiveConfigParser(configparser.ConfigParser):
    optionxform = staticmethod(str)


class INIConfigIO(ConfigIO):
    def write(self, path: Path, data: _RAW_CONFIG_T):
        cp = _CaseSensitiveConfigParser()

        for key_or_section, value_or_content in data.items():
            if isinstance(value_or_content, Mapping):
                cp.add_section(key_or_section)
                for key, value in value_or_content.items():
                    cp.set(key_or_section, key, str(value))
            else:
                cp.set("", key_or_section, value_or_content)

        with path.open("w") as out:
            cp.write(out)

    def read(self, path: Path) -> _RAW_CONFIG_T:
        data = {}
        cp = _CaseSensitiveConfigParser()
        cp.read(str(path))
        for section_name, section_values in cp.items():
            if section_name and section_name != cp.default_section:
                data[section_name] = {**section_values}
            else:
                data.update(section_values)

        return data


class _WheelBoolFieldCodec(ConfigFieldCodec):

    def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> _T:
        return v == 'true'

    def unparse(self, parent: ConfigCodec, type_: Type, v: _T) -> Any:
        return 'true' if v else 'false'


_WheelBoolFieldCodec = _WheelBoolFieldCodec()


class WheelFileConfigIO(ConfigIO):

    def __init__(self, *, codec: ConfigCodec = None):
        super().__init__(codec=(codec or ConfigCodec()).extended({bool: _WheelBoolFieldCodec}))

    def write(self, path: Path, data: _RAW_CONFIG_T):
        path.write_text(os.linesep.join(f'{k}: {v}' for k, v in data.items()))

    def read(self, path: Path) -> _RAW_CONFIG_T:
        seperator_rx = re.compile("\\s*:\\s*")
        lines = (line.strip() for line in path.read_text().splitlines())
        kvs = (seperator_rx.split(kv) for kv in lines if kv)
        return {k: v for k, v in kvs}


class CSVConfigIO(ConfigIO):

    def __init__(self, *headers: str, codec: ConfigCodec = None):
        super().__init__(
            codec=(codec or ConfigCodec()).extended({bool: StringableFieldCodec, int: StringableFieldCodec}))
        self._headers = headers

    def write(self, path: Path, data: _RAW_CONFIG_T):
        with path.open('w+', newline='') as new_record_fd:
            for record in data['records']:
                csv.writer(new_record_fd).writerow(record[c] for c in self._headers)

    def read(self, path: Path) -> _RAW_CONFIG_T:
        with path.open('r', newline='') as records_fd:
            return {
                "records": [
                    {self._headers[i]: c for i, c in enumerate(record)} for record in csv.reader(records_fd)]}
