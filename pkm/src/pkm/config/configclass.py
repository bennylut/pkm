from __future__ import annotations

import typing
from abc import abstractmethod, ABC
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar, Dict, Any, Type, Generic, List, Mapping, Optional, Callable, Protocol, Union

from pkm.utils.commons import NoSuchElementException

_T = TypeVar("_T")
_RAW_CONFIG_T = Dict[str, Any]
_CONFIG_SCHEMA_FIELD = "__config_schema__"


class Stringable(Protocol):
    def __init__(self, v: str):
        ...

    def __str__(self) -> str:
        ...


class ConfigFile(Protocol):
    def save(self, path: Path = None):
        ...

    def reload(self):
        ...


class ConfigFieldCodec(Generic[_T]):

    @abstractmethod
    def decode(self, parent: ConfigCodec, type_: Type, v: Any) -> _T:
        ...

    @abstractmethod
    def encode(self, parent: ConfigCodec, type_: Type, v: _T) -> Any:
        ...


class _IDFieldCodec(ConfigFieldCodec[Any]):

    def decode(self, parent: ConfigCodec, type_: Type, v: Any) -> Any:
        return v

    def encode(self, parent: ConfigCodec, type_: Type, v: Any) -> Any:
        return v


_IDFieldCodec = _IDFieldCodec()


class _StringableFieldCodec(ConfigFieldCodec[Stringable]):

    def decode(self, parent: ConfigCodec, type_: Type, v: Any) -> Stringable:
        return type_(str(v))

    def encode(self, parent: ConfigCodec, type_: Type, v: Stringable) -> Any:
        return str(v)


_StringableFieldCodec = _StringableFieldCodec()


class _ListFieldCodec(ConfigFieldCodec[List]):

    def decode(self, parent: ConfigCodec, type_: Type, v: Any) -> List:
        element_type = typing.get_args(type_)[0]
        element_codec = parent.field_codec_for(element_type)
        return [element_codec.decode(parent, element_type, it) for it in v]

    def encode(self, parent: ConfigCodec, type_: Type, v: List) -> Any:
        element_type = typing.get_args(type_)[0]
        element_codec = parent.field_codec_for(element_type)
        return [element_codec.encode(parent, element_type, it) for it in v]


class _DictFieldCodec(ConfigFieldCodec[Dict]):

    def decode(self, parent: ConfigCodec, type_: Type, v: Any) -> Dict:
        key_type, value_type = typing.get_args(type_)
        key_codec, value_codec = parent.field_codec_for(key_type), parent.field_codec_for(value_type)
        return {key_codec.decode(parent, key_type, k): value_codec.decode(parent, value_type, i) for k, i in v.items()}

    def encode(self, parent: ConfigCodec, type_: Type, v: Dict) -> Any:
        key_type, value_type = typing.get_args(type_)
        key_codec, value_codec = parent.field_codec_for(key_type), parent.field_codec_for(value_type)
        return {
            key_codec.encode(parent, key_type, k): value_codec.encode(parent, value_type, i) for k, i in v.items()}


_COMMON_CODECS: Dict[Type, ConfigFieldCodec] = {
    str: _IDFieldCodec, int: _IDFieldCodec, bool: _IDFieldCodec, dict: _DictFieldCodec(), list: _ListFieldCodec(),
    Path: _StringableFieldCodec
}


class ConfigIO(ABC):

    def __init__(self, codec: ConfigCodec):
        self.codec = codec

    @abstractmethod
    def write(self, path: Path, data: _RAW_CONFIG_T):
        ...

    @abstractmethod
    def read(self, path: Path) -> _RAW_CONFIG_T:
        ...

    def load(self, path: Path, type_: Type[_T], target_object: _T = None) -> Union[ConfigFile, _T]:
        encoded = self.read(path)
        decoded = self.codec.decode(encoded, type_, target_object)
        decoded.save = lambda target_path: self.write(target_path or path, self.codec.encode(decoded))
        decoded.reload = lambda: self.load(path, type_, decoded)


class ConfigCodec:

    def __init__(self, field_codecs: Mapping[Type, ConfigFieldCodec] = None):
        self._field_codecs = field_codecs or {}

    def field_codec_for(self, type_: Type) -> ConfigFieldCodec:
        if not (result := self.field_codec_for_or_none(type_)):
            raise NoSuchElementException(f"could not find codec for type: {type_}")

        return result

    def field_codec_for_or_none(self, type_: Type) -> Optional[ConfigFieldCodec]:
        result = self._field_codecs.get(type_) or _COMMON_CODECS.get(type_)
        if not result and (origin := typing.get_origin(type_)):
            result = self.field_codec_for(origin)

        return result

    def decode(self, config: _RAW_CONFIG_T, target_class: Type[_T], target_object: _T = None) -> _T:
        field_schema: Dict[str, _ConfigFieldSchema] = getattr(target_class, _CONFIG_SCHEMA_FIELD)

        target_object = target_object or target_class()
        for field, schema in field_schema.items():
            value = config.get(field, None)

            if value is None:
                if schema.required:
                    raise ValueError(f"required field is missing: {field}")
                elif schema.default_factory:
                    value = schema.default_factory()
                else:
                    value = schema.default
            else:
                if codec := schema.codec or self.field_codec_for_or_none(schema.type):
                    value = codec.decode(self, schema.type, value)
                elif hasattr(schema.type, _CONFIG_SCHEMA_FIELD):
                    value = self.decode(value, schema.type)
                else:
                    raise ValueError(f"no codec could be found for type: {schema.type}")

            setattr(target_object, field, value)

        return target_object

    def encode(self, config_object: Any) -> _RAW_CONFIG_T:
        target_config = {}
        field_schema: Dict[str, _ConfigFieldSchema] = getattr(type(config_object), _CONFIG_SCHEMA_FIELD)

        for field, schema in field_schema.items():
            value = getattr(config_object, field, None)
            if value is not None:
                if codec := schema.codec or self.field_codec_for_or_none(schema.type):
                    value = codec.encode(self, schema.type, value)
                elif hasattr(schema.type, _CONFIG_SCHEMA_FIELD):
                    value = self.encode(value)
                else:
                    raise ValueError(f"no codec could be found for type: {schema.type}")

                target_config[field] = value
        return target_config


@dataclass
class _ConfigFieldSchema:
    required: bool = False
    codec: Optional[ConfigFieldCodec] = None
    default: Optional[Any] = None
    default_factory: Optional[Callable[[], Any]] = None
    type: Type[_T] = None


def configvar(
        required: bool = False, codec: ConfigFieldCodec = None, default: Any = None,
        default_factory: Callable[[], Any] = None) -> Any:
    return _ConfigFieldSchema(**locals())


def configclass(cls: Type[_T]) -> Type[_T]:
    fields: Dict[str, Type] = typing.get_type_hints(cls)
    config_schema = {}
    for field, type_ in fields.items():
        schema = getattr(cls, field, None) or _ConfigFieldSchema()
        setattr(cls, field, None)  # remove before applying dataclass
        schema.type = type_

        config_schema[field] = schema

    setattr(cls, _CONFIG_SCHEMA_FIELD, config_schema)
    return dataclass(cls)


if __name__ == '__main__':
    @configclass
    class YYY:
        l: List[str]
        d: Dict[int, List[str]]


    @configclass
    class XXX:
        x: int = configvar(required=True)
        y: Path
        yyy: YYY


    cc = ConfigCodec()
    xxx = XXX(1, Path("hello"), YYY(["a", "b"], {1: ["x", "y"]}))

    print(cc.encode(xxx))
    print(cc.decode(cc.encode(xxx), XXX))
