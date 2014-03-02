import struct
from collections import namedtuple
from contextlib import contextmanager

from .common import align


IFF_NATIVE_ENDIAN = 0
IFF_BIG_ENDIAN = 1
IFF_LITTLE_ENDIAN = 2

IffFormat = namedtuple("IffFormat", ["endianness", "alignment",
                                     "typeid_bytes", "size_bytes"])

IffChunk = namedtuple("IffChunk", ["typeid", "data_offset", "data_length"])


def _get_header_format(format):
    endian_formats = {IFF_NATIVE_ENDIAN: "=",
                      IFF_BIG_ENDIAN: ">",
                      IFF_LITTLE_ENDIAN: "<"}
    byte_formats = {1: "B", 2: "H", 4: "L", 8: "Q"}

    if format.endianness not in endian_formats:
        raise ValueError, "Iff: Invalid endianness"

    if format.typeid_bytes not in byte_formats:
        raise ValueError, "Iff: Invalid typeid format"

    if format.size_bytes not in byte_formats:
        raise ValueError, "Iff: Invalid size format"

    fmt = (endian_formats[format.endianness] +
           byte_formats[format.typeid_bytes] +
           byte_formats[format.size_bytes])
    size = format.typeid_bytes + format.size_bytes

    return fmt, size


class IffParser(object):

    def __init__(self, stream, format):
        self.__stream = stream
        self.__format = format
        self.__header_fmt, self.__header_size = _get_header_format(format)
        self.__current_chunk = None
        self.__current_chunk_end = None
        self.__chunk_handlers = {}

    @property
    def stream(self):
        return self.__stream

    @property
    def chunk(self):
        return self.__current_chunk

    def reset(self):
        self.__current_chunk = None
        self.__current_chunk_end = None
        self.__stream.seek(0)

    def parse(self):
        self.reset()
        self._handle_all_chunks()

    def on_iff_chunk(self, chunk):
        pass

    def _handle_all_chunks(self, types=None, alignment=None):
        for chunk in self._iter_chunks(types=types):
            self._get_chunk_handler(chunk.typeid)(chunk)

    def _handle_next_chunk(self, alignment=None):
        chunk = self._read_next_chunk()
        if chunk:
            with self._using_chunk(chunk, alignment=alignment):
                self._get_chunk_handler(chunk.typeid)(chunk)
                return True
        return False

    def _register_chunk_handler(self, typeid, callback):
        self.__chunk_handlers[typeid] = callback

    def _get_chunk_handler(self, typeid):
        return self.__chunk_handlers.get(typeid, self.on_iff_chunk)

    def _iter_chunks(self, types=None):
        chunk = self._read_next_chunk()
        while chunk:
            with self._using_chunk(chunk):
                if types is None or chunk.typeid in types:
                    yield chunk
            chunk = self._read_next_chunk()

    @contextmanager
    def _using_chunk(self, chunk):
        data_end = chunk.data_offset + chunk.data_length
        chunk_end = chunk.data_offset + align(chunk.data_length, self.__format.alignment)
        try:
            old_chunk = self.__current_chunk
            old_chunk_end = self.__current_chunk_end
            self.__current_chunk = chunk
            self.__current_chunk_end = chunk_end
            self._set_offset(chunk.data_offset)
            yield chunk
        finally:
            chunk_end = self.__current_chunk_end
            self.__current_chunk = old_chunk
            self.__current_chunk_end = old_chunk_end
            self._set_offset(chunk_end)

    def _realign(self):
        chunk = self.__current_chunk
        base_offset = self._get_offset()
        base_delta = chunk.data_offset + chunk.data_length - base_offset
        self.__current_chunk_end = base_offset + align(base_delta, self.__format.alignment)

    def _read_chunk_data(self, chunk=None):
        chunk = chunk or self.__current_chunk
        if chunk:
            self.__stream.seek(chunk.data_offset)
            return self.__stream.read(chunk.data_length)
        else:
            return ""

    def _read_next_chunk(self):
        if self._is_past_the_end():
            return None

        header = self._read_next_chunk_header()
        if not header:
            return None
        
        typeid, data_length = header
        data_offset = self._get_offset()
        return IffChunk(typeid=typeid,
                        data_offset=data_offset,
                        data_length=data_length)

    def _read_next_chunk_header(self):
        buf = self.__stream.read(self.__header_size)
        if len(buf) == self.__header_size:
            return struct.unpack(self.__header_fmt, buf)
        else:
            return None

    def _is_past_the_end(self):
        if self.__current_chunk_end:
            return self._get_offset() >= self.__current_chunk_end
        else:
            return not self.__stream

    def _get_offset(self):
        return self.__stream.tell()

    def _set_offset(self, offset):
        self.__stream.seek(offset)
