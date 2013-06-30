import struct


def be_word4(buf):
    return struct.unpack(">L", buf)[0]


def le_word4(buf):
    return struct.unpack("<L", buf)[0]


def be_word8(buf):
    return struct.unpack(">Q", buf)[0]


def le_word8(buf):
    return struct.unpack("<Q", buf)[0]


def be_read4(stream):
    return struct.unpack(">L", stream.read(4))[0]


def le_read4(stream):
    return struct.unpack("<L", stream.read(4))[0]


def be_read8(stream):
    return struct.unpack(">Q", stream.read(8))[0]


def le_read8(stream):
    return struct.unpack("<Q", stream.read(8))[0]


def align(size, stride):
    return stride * int(1 + ((size - 1) / stride))


def read_null_terminated(stream):
    result = ""
    next = stream.read(1)
    while stream and next != '\0':
        result += next
        next = stream.read(1)
    return result
