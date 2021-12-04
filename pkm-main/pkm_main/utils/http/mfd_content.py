from collections import deque
from io import IOBase
from typing import List, Deque, Optional, Iterator, Dict, Tuple, Union
from uuid import uuid4

from urllib3.fields import RequestField


class MFDContent(IOBase):
    def __init__(self, fields: List[RequestField], chunk_size: int = 8092, boundary: Optional[str] = None):
        self._fields = fields
        self._chunk_size = chunk_size
        self._boundary = boundary or uuid4().hex
        self._buffer = _Buffer()

        fill = self._filler()
        self._fill = lambda: next(fill, False)

    def content_type(self):
        return f"multipart/form-data; boundary={self._boundary}"

    @classmethod
    def from_fields_dict(cls, fields_dict: Dict[str, Union[RequestField, Tuple]], **init_kwargs) -> "MFDContent":
        return MFDContent([RequestField.from_tuples(key, value) for key, value in fields_dict.items()], **init_kwargs)

    @classmethod
    def from_fields_list(cls, fields_dict: List[Union[Tuple, RequestField]], **init_kwargs) -> "MFDContent":
        return MFDContent([RequestField.from_tuples(*value) for value in fields_dict], **init_kwargs)

    def _filler(self) -> Iterator[bool]:
        boundary = f"--{self._boundary}\r\n".encode()
        newline = b"\r\n"
        buffer = self._buffer
        chunk_size = self._chunk_size

        for field in self._fields:
            buffer.write(boundary)
            buffer.write(field.render_headers().encode())

            field_data = field.data
            if field_data is None:
                field_data = ''

            if isinstance(field_data, IOBase):
                while True:
                    chunk = field_data.read(chunk_size)

                    if not chunk:
                        break

                    if isinstance(chunk, str):
                        chunk = chunk.encode()
                    buffer.write(chunk)
                    yield True
            elif isinstance(field_data, str):
                buffer.write(field_data.encode())
            elif isinstance(field_data, bytes):
                buffer.write(field_data)
            else:
                raise ValueError(f"unsupported field data type: {type(field_data)}")

            buffer.write(newline)

        yield True

    def read(self, size: int = -1) -> memoryview:
        buffer = self._buffer

        if size < 0:
            while self._fill():
                continue

            return buffer.read(buffer.remaining_bytes)

        while buffer.remaining_bytes < size:
            if not self._fill():
                break

        return buffer.read(min(size, buffer.remaining_bytes))


_NOTHING = memoryview(bytearray(0))


class _Buffer:

    def __init__(self):
        self._chunks: Deque[bytes] = deque()
        self._current_chunk: memoryview = _NOTHING
        self._current_chunk_offset: int = 0
        self.remaining_bytes: int = 0

    def write(self, data: bytes):
        self.remaining_bytes += len(data)
        self._chunks.append(data)

    def read(self, size: int, into: Optional[memoryview] = None) -> memoryview:
        if size == 0:
            return _NOTHING

        current_chunk_offset = self._current_chunk_offset
        current_chunk = self._current_chunk
        left_in_current_chunk = len(current_chunk) - current_chunk_offset
        if left_in_current_chunk >= size:
            result = current_chunk[current_chunk_offset:current_chunk_offset + size]
            self._current_chunk_offset += size
            self.remaining_bytes -= size

            if into:
                into[:size] = result
                return into

            return result

        if left_in_current_chunk == 0:
            self._current_chunk = memoryview(self._chunks.popleft())
            self._current_chunk_offset = 0
            return self.read(size, into)

        into = memoryview(bytearray(size)) if into is None else into
        into[:left_in_current_chunk] = current_chunk[current_chunk_offset:]
        self._current_chunk = memoryview(self._chunks.popleft())
        self._current_chunk_offset = 0
        self.remaining_bytes -= left_in_current_chunk
        self.read(size - left_in_current_chunk, into[left_in_current_chunk:])
        return into
