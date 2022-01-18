import hashlib
import io
import re
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, IO, Union

from pkm.utils.io_streams import chunks

_SIG_DELIM_RX = re.compile("\\s*=\\s*")


class HashDigester(Protocol):
    def digest(self) -> bytes:
        ...

    def hexdigest(self) -> str:
        ...

    def update(self, __data: Union[bytes, bytearray, memoryview]) -> None:
        ...


def stream(hd: HashDigester, file: Union[IO, Path], chunk_size: int = io.DEFAULT_BUFFER_SIZE):
    """
    streams a file into `hd` (via `hd.update(chunk)`) using chunks of the given `chunk_size`
    :param hd: the hash digester to stream into
    :param file: the file to stream
    :param chunk_size: the size of the chunk to use, defaults to `io.DEFAULT_BUFFER_SIZE`
    """
    if isinstance(file, Path):
        with file.open('rb') as source_fd:
            stream(hd, source_fd, chunk_size)
    else:
        for chunk in chunks(file, chunk_size):
            hd.update(chunk)


@dataclass
class HashSignature:
    hash_type: str
    hash_value: str

    def _encode_hash(self, hashd: HashDigester) -> str:
        return type(self).encode_hash(hashd)

    def validate_against(self, file: Path) -> bool:
        if not hasattr(hashlib, self.hash_type):
            raise KeyError(f"Cannot validate archive, Unsupported Hash {self.hash_type}")

        hash_computer = getattr(hashlib, self.hash_type)()
        stream(hash_computer, file)
        computed_hash = self._encode_hash(hash_computer)
        return computed_hash == self.hash_value

    def __str__(self):
        return f"{self.hash_type}={self.hash_value}"

    def __repr__(self):
        return f"HashSignature({self})"

    @classmethod
    def encode_hash(cls, hashd: HashDigester):
        return hashd.hexdigest()

    @classmethod
    def parse_hex_encoded(cls, signature: str) -> "HashSignature":
        parts = _SIG_DELIM_RX.split(signature)
        if len(parts) != 2:
            raise ValueError('unsupported signature, expecting format <hash_type>=<hash_value>')

        return HashSignature(*parts)

    @classmethod
    def parse_urlsafe_base64_nopad_encoded(cls, signature: str) -> "HashSignature":
        parts = _SIG_DELIM_RX.split(signature)
        if len(parts) != 2:
            raise ValueError(f'unsupported signature, expecting format <hash_type>=<hash_value>, got: {signature}')

        return _UrlsafeBase64NopadHashSignature(*parts)

    @classmethod
    def create_urlsafe_base64_nopad_encoded(cls, hash_function: str, file: Path) -> "HashSignature":
        hashd = getattr(hashlib, hash_function)()
        stream(hashd, file)
        encoded = _UrlsafeBase64NopadHashSignature.encode_hash(hashd)
        return _UrlsafeBase64NopadHashSignature(hash_function, encoded)


class _UrlsafeBase64NopadHashSignature(HashSignature):

    @classmethod
    def encode_hash(cls, hashd: HashDigester):
        return urlsafe_b64encode(hashd.digest()).decode("latin1").rstrip("=")
