from __future__ import annotations

import dataclasses
import typing
from abc import abstractmethod, ABC
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TypeVar, Dict, Any, Type, Generic, List, Mapping, Optional, Callable, Protocol

from pkm.utils.commons import NoSuchElementException, UnsupportedOperationException
from pkm.utils.enums import enum_by_name
from pkm.utils.ipc import IPCPackable
from pkm.utils.properties import clear_cached_properties

_T = TypeVar("_T")
_RAW_CONFIG_T = Dict[str, Any]
_CONFIG_SCHEMA_FIELD = "__config_schema__"
_CONFIG_IO_FIELD = "__config_io__"


# noinspection PyUnusedLocal
class Stringable(Protocol):
    @abstractmethod
    def __init__(self, v: str):
        ...

    @abstractmethod
    def __str__(self) -> str:
        ...


# noinspection PyShadowingNames
class ConfigFile(ABC, IPCPackable):
    _path: Path

    def __getstate__(self):
        return [self.to_config(), self.path]

    def __setstate__(self, state):
        cls = type(self)
        cls._io().codec.parse(state[0], cls, self)
        self.path = state[1]

    def save(self, path: Path = None):
        path = path or self.path
        path.parent.mkdir(exist_ok=True, parents=True)
        type(self)._io().save(path, self)

    def to_config(self) -> _RAW_CONFIG_T:
        return type(self)._io().codec.unparse(self)

    def reload(self):
        type(self).load(self._path, target_object=self)
        clear_cached_properties(self)

    @property
    def path(self) -> Optional[Path]:
        return getattr(self, "_path", None)

    @path.setter
    def path(self, v: Path):
        self._path = v

    @classmethod
    def _io(cls) -> ConfigIO:
        if not (io := getattr(cls, _CONFIG_IO_FIELD, None)):
            raise UnsupportedOperationException("no io provided on config_class decorator")
        return io

    @classmethod
    def load(cls, path: Path, *, target_object: ConfigFile = None) -> ConfigFile:
        result = cls._io().load(path, cls, target_object)
        result._path = path
        return result

    @classmethod
    def from_config(cls, config: _RAW_CONFIG_T, path: Optional[Path] = None) -> ConfigFile:
        result = cls._io().codec.parse(config, cls)
        result.path = path
        return result


class ConfigFieldCodec(Generic[_T]):

    @abstractmethod
    def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> _T:
        ...

    @abstractmethod
    def unparse(self, parent: ConfigCodec, type_: Type, v: _T) -> Any:
        ...


class _IDFieldCodec(ConfigFieldCodec[Any]):

    def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> Any:
        return v

    def unparse(self, parent: ConfigCodec, type_: Type, v: Any) -> Any:
        return v


_IDFieldCodec = _IDFieldCodec()


class StringableFieldCodec(ConfigFieldCodec[Stringable]):

    def parse(self, parent: ConfigCodec, type_: Type, v: str) -> Optional[Stringable]:
        if len(v) == 0:
            return None

        return type_(str(v))

    def unparse(self, parent: ConfigCodec, type_: Type, v: Optional[Stringable]) -> str:
        if v is None:
            return ''

        return str(v)


StringableFieldCodec = StringableFieldCodec()


class _ListFieldCodec(ConfigFieldCodec[List]):

    def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> List:
        element_type = typing.get_args(type_)[0]
        element_codec = parent.field_codec_for(element_type)
        return [element_codec.parse(parent, element_type, it) for it in v]

    def unparse(self, parent: ConfigCodec, type_: Type, v: List) -> Any:
        element_type = typing.get_args(type_)[0]
        element_codec = parent.field_codec_for(element_type)
        return [element_codec.unparse(parent, element_type, it) for it in v]


class _DictFieldCodec(ConfigFieldCodec[Dict]):

    def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> Dict:
        arg_types = typing.get_args(type_)

        if len(arg_types) != 2:
            raise UnsupportedOperationException(f"argument type was not supplied for dict (type={type_})")

        assert isinstance(v, Mapping), f"expecting value of type dict, got {type(v)} [{v}]"

        key_type, value_type = typing.get_args(type_)
        key_codec, value_codec = parent.field_codec_for(key_type), parent.field_codec_for(value_type)
        return {key_codec.parse(parent, key_type, k): value_codec.parse(parent, value_type, i) for k, i in v.items()}

    def unparse(self, parent: ConfigCodec, type_: Type, v: Dict) -> Any:
        assert isinstance(v, Mapping)

        key_type, value_type = typing.get_args(type_)
        key_codec, value_codec = parent.field_codec_for(key_type), parent.field_codec_for(value_type)
        return {
            key_codec.unparse(parent, key_type, k): value_codec.unparse(parent, value_type, i) for k, i in v.items()}


class _ParsableFieldCodec(ConfigFieldCodec):

    def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> _T:
        return type_.parse(v)  # noqa

    def unparse(self, parent: ConfigCodec, type_: Type, v: _T) -> Any:
        return str(v)


_ParsableFieldCodec = _ParsableFieldCodec()


class _EnumFieldCodec(ConfigFieldCodec):

    def parse(self, parent: ConfigCodec, type_: Type[Enum], v: Any) -> _T:
        return enum_by_name(type_, v)

    def unparse(self, parent: ConfigCodec, type_: Type, v: _T) -> Any:
        return v.name


_EnumFieldCodec = _EnumFieldCodec()


class _ComplexFieldCodec(ConfigFieldCodec):

    def parse(self, parent: ConfigCodec, type_: Type[_T], v: Dict[str, Any]) -> _T:
        return parent.parse(v, type_)

    def unparse(self, parent: ConfigCodec, type_: Type, v: _T) -> Dict[str, Any]:
        return parent.unparse(v)


_ComplexFieldCodec = _ComplexFieldCodec()


def config_field_codec(parse: Callable[[Any], _T], unparse: Callable[[_T], Any]) -> ConfigFieldCodec:
    class _SimpleConfigFieldCodec(ConfigFieldCodec):
        def parse(self, parent: ConfigCodec, type_: Type, v: Any) -> _T:
            return parse(v)

        def unparse(self, parent: ConfigCodec, type_: Type, v: _T) -> Any:
            return unparse(v)

    return _SimpleConfigFieldCodec()


_COMMON_CODECS: Optional[Dict[Type, ConfigFieldCodec]] = None


def _common_codecs() -> Dict[Type, ConfigFieldCodec]:
    from pkm.api.dependencies.dependency import Dependency
    from pkm.api.packages.package import PackageDescriptor
    from pkm.api.versions.version import Version
    from pkm.api.versions.version_specifiers import VersionSpecifier

    global _COMMON_CODECS
    global _common_codecs  # noqa
    _COMMON_CODECS = {
        str: _IDFieldCodec, int: _IDFieldCodec, bool: _IDFieldCodec, dict: _DictFieldCodec(), list: _ListFieldCodec(),
        Path: StringableFieldCodec, Version: _ParsableFieldCodec, Dependency: _ParsableFieldCodec,
        VersionSpecifier: _ParsableFieldCodec, Any: _IDFieldCodec,
        PackageDescriptor: config_field_codec(PackageDescriptor.read, lambda v: v.write())}

    _common_codecs = lambda: _COMMON_CODECS  # noqa
    return _COMMON_CODECS


class ConfigIO(ABC):

    def __init__(self, *, codec: ConfigCodec = None):
        self.codec = codec or ConfigCodec()

    @abstractmethod
    def write(self, path: Path, data: _RAW_CONFIG_T):
        ...

    @abstractmethod
    def read(self, path: Path) -> _RAW_CONFIG_T:
        ...

    def load(self, path: Path, type_: Type[_T], target_object: _T = None) -> _T:
        encoded = self.read(path) if path.exists() else {}
        return self.codec.parse(encoded, type_, target_object)

    def save(self, path: Path, obj: _T):
        path.parent.mkdir(exist_ok=True, parents=True)
        self.write(path, self.codec.unparse(obj))


def _pop_key(config_: _RAW_CONFIG_T, key: str) -> Any:
    parts = key.split('.')
    for i in range(len(parts) - 1):
        if not (config_ := config_.get(parts[i], None)):
            return None
        assert isinstance(config_, Mapping)

    return config_.pop(parts[-1], None)


def _shove_key(config_: _RAW_CONFIG_T, key: str, value: Any):
    parts = key.split('.')
    for i in range(len(parts) - 1):
        if not (next_config := config_.get(parts[i], None)):
            config_[parts[i]] = next_config = {}

        config_ = next_config

    config_[parts[-1]] = value


class ConfigCodec:

    def __init__(self, field_codecs: Mapping[Type, ConfigFieldCodec] = None):
        self._field_codecs = field_codecs or {}

    def field_codec_for(self, type_: Type) -> ConfigFieldCodec:
        if not (result := self.field_codec_for_or_none(type_)):
            raise NoSuchElementException(f"could not find codec for type: {type_}")

        return result

    def extended(self, field_codecs: Mapping[Type, ConfigFieldCodec]) -> ConfigCodec:
        return ConfigCodec({**self._field_codecs, **field_codecs})

    def field_codec_for_or_none(self, type_: Type) -> Optional[ConfigFieldCodec]:
        try:
            if issubclass(type_, Enum):
                return _EnumFieldCodec
        except Exception:  # noqa
            pass

        while type_:
            if not (result := self._field_codecs.get(type_) or _common_codecs().get(type_)):
                if hasattr(type_, _CONFIG_SCHEMA_FIELD):
                    return _ComplexFieldCodec
                type_ = typing.get_origin(type_)
            else:
                return result
        return None

    def parse(self, config_: _RAW_CONFIG_T, target_class: Type[_T], target_object: _T = None) -> _T:
        field_schema: Dict[str, ConfigField] = getattr(target_class, _CONFIG_SCHEMA_FIELD)

        target_object = target_object or target_class()
        for field, schema in field_schema.items():

            if schema.leftover:
                value = config_
            else:
                key = schema.key or field
                value = _pop_key(config_, key)

                if value is None:
                    if schema.required:
                        raise ValueError(f"required field is missing: {field}")
                    elif schema.default_factory:
                        value = schema.default_factory()
                    else:
                        value = schema.default
                else:
                    codec = schema.codec or self.field_codec_for_or_none(schema.type)
                    if not codec:
                        raise NoSuchElementException(f"could not find codec for field: {field} with type {schema.type}")

                    try:
                        value = codec.parse(self, schema.type, value)
                    except Exception as e:
                        raise ValueError(
                            f"could not parse config ({target_class.__name__}), "
                            f"parsing field: '{field}' into type: '{schema.type}' failed") from e

            setattr(target_object, field, value)

        return target_object

    def unparse(self, config_object: Any) -> _RAW_CONFIG_T:
        target_config = {}
        field_schema: Dict[str, ConfigField] = getattr(type(config_object), _CONFIG_SCHEMA_FIELD)

        for field, schema in field_schema.items():
            value = getattr(config_object, field, None)
            if value is not None:
                if schema.leftover:
                    target_config.update(value)
                    continue
                elif codec := schema.codec or self.field_codec_for_or_none(schema.type):
                    try:
                        value = codec.unparse(self, schema.type, value)
                    except Exception as e:
                        raise ValueError(
                            f"could not unparse field '{field}' of expected type "
                            f"'{schema.type}' from value {value}") from e

                elif hasattr(schema.type, _CONFIG_SCHEMA_FIELD):
                    value = self.unparse(value)
                else:
                    raise ValueError(f"no codec could be found for type: {schema.type}")

                _shove_key(target_config, schema.key or field, value)
        return target_config


@dataclass
class ConfigField:
    required: bool = False
    codec: Optional[ConfigFieldCodec] = None
    default: Optional[Any] = None
    default_factory: Optional[Callable[[], Any]] = None
    type: Type[_T] = None
    leftover: bool = False
    key: str = None

    def to_dataclass_field(self) -> dataclasses.Field:
        if self.default_factory:
            return dataclasses.field(default_factory=self.default_factory)  # noqa

        return dataclasses.field(default=self.default)  # noqa


def config_field(
        *, required: bool = False, codec: ConfigFieldCodec = None, default: Any = None,
        default_factory: Callable[[], Any] = None, leftover: bool = False, key: str = None) -> Any:
    return ConfigField(**locals())


def config(cls: Type[_T] = None, *, io: ConfigIO = None) -> Type[_T]:
    """
    important note: if you want to apply both config and dataclass, use first dataclass and then config
    """

    def decorator(cls_):
        annotated_fields: Dict[str, Type] = typing.get_type_hints(cls_)

        config_schema = {}
        for field, type_ in annotated_fields.items():
            schema = getattr(cls_, field, None)
            if schema or not field.startswith("_"):

                if schema is None:
                    schema = ConfigField()
                elif not isinstance(schema, ConfigField):
                    schema = ConfigField(default=schema)

                setattr(cls_, field, schema.to_dataclass_field())  # remove before applying dataclass
                schema.type = type_
                config_schema[field] = schema

        for field, value in cls_.__dict__.items():
            if field not in annotated_fields and isinstance(value, ConfigField):
                if value.leftover:
                    setattr(cls_, field, None)  # remove before applying dataclass
                    value.type = dict
                    config_schema[field] = value
                else:
                    raise UnsupportedOperationException(f"untyped configuration field : {field}")

        setattr(cls_, _CONFIG_IO_FIELD, io)
        setattr(cls_, _CONFIG_SCHEMA_FIELD, config_schema)
        return cls_

    return decorator(cls) if cls else decorator
