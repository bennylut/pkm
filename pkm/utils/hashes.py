import hashlib
import re
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pkm.logging.console import console

_SIG_DELIM_RX = re.compile("\\s*=\\s*")


class HashDigester(Protocol):
    def digest(self) -> bytes:
        ...

    def hexdigest(self) -> str:
        ...


@dataclass
class HashSignature:
    hash_type: str
    hash_value: str

    def _encode_hash(self, hash: HashDigester) -> str:
        return hash.hexdigest()

    def validate_against(self, file: Path) -> bool:
        if not hasattr(hashlib, self.hash_type):
            raise KeyError(f"Cannot validate archive, Unsupported Hash {self.hash_type}")

        hash_computer = getattr(hashlib, self.hash_type)()
        with file.open('rb') as source_fd:
            while chunk := source_fd.read(8192):
                hash_computer.update(chunk)

        computed_hash = self._encode_hash(hash_computer)
        eqhash = computed_hash == self.hash_value
        if not eqhash:
            console.log(f"Warning: {file} signature does not correspond to its actual content ({computed_hash} != {self.hash_value})")

        return eqhash

    def __str__(self):
        return f"{self.hash_type}={self.hash_value}"

    def __repr__(self):
        return f"HashSignature({self})"

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
            raise ValueError('unsupported signature, expecting format <hash_type>=<hash_value>')

        return _UrlsafeBase64NopadHashSignature(*parts)


class _UrlsafeBase64NopadHashSignature(HashSignature):
    def _encode_hash(self, hash: HashDigester) -> str:
        return urlsafe_b64encode(hash.digest()).decode("latin1").rstrip("=")
