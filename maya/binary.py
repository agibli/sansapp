import os
import re
import sys
import struct
from functools import wraps
from contextlib import contextmanager
from collections import namedtuple

from common import *
from ..util.iff import *
from ..util import *


# IFF chunk type IDs
FOR4 = be_word4("FOR4")
LIS4 = be_word4("LIS4")
# 64 bits
FOR8 = be_word4("FOR8")
LIS8 = be_word4("LIS8")

# General
MAYA = be_word4("Maya")

# File referencing
FREF = be_word4("FREF")
FRDI = be_word4("FRDI")

# Header fields
HEAD = be_word4("HEAD")
VERS = be_word4("VERS")
PLUG = be_word4("PLUG")
FINF = be_word4("FINF")
AUNI = be_word4("AUNI")
LUNI = be_word4("LUNI")
TUNI = be_word4("TUNI")

# Node creation
CREA = be_word4("CREA")
SLCT = be_word4("SLCT")
ATTR = be_word4("ATTR")

CONS = be_word4("CONS")
CONN = be_word4("CONN")

# Data types
FLGS = be_word4("FLGS")
DBLE = be_word4("DBLE")
DBL3 = be_word4("DBL3")
STR_ = be_word4("STR ")
FLT2 = be_word4("FLT2")
CMPD = be_word4("CMPD")
MESH = be_word4("MESH")


MAYA_BINARY_32 = IffFormat(endianness=IFF_BIG_ENDIAN,
                           typeid_bytes=4,
                           size_bytes=4,
                           header_alignment=4,
                           chunk_alignment=4)
MAYA_BINARY_64 = IffFormat(endianness=IFF_BIG_ENDIAN,
                           typeid_bytes=4,
                           size_bytes=8,
                           header_alignment=8,
                           chunk_alignment=8)


class MayaBinaryError(RuntimeError):
    pass


class MayaBinaryParser(IffParser, MayaParserBase):
    def __init__(self, stream):
        # Determine Maya format based on magic number
        # Maya 2014+ files begin with a FOR8 block, indicating a 64-bit format.
        magic_number = stream.read(4)
        stream.seek(0)
        if magic_number == "FOR4":
            format = MAYA_BINARY_32
        elif magic_number == "FOR8":
            format = MAYA_BINARY_64
        else:
            raise MayaBinaryError, "Bad magic number"

        IffParser.__init__(self, stream, format=format)
        MayaParserBase.__init__(self)

        maya64 = format == MAYA_BINARY_64
        self.__maya64 = maya64
        self.__node_chunk_type = FOR8 if maya64 else FOR4
        self.__list_chunk_type = LIS8 if maya64 else LIS4

        # FIXME load type info modules based on maya and plugin versions
        self.__mtypeid_to_typename = {}
        self._load_mtypeid_database(os.path.join(os.path.dirname(__file__),
                                    "modules", "maya", "2012", "typeids.dat"))

    def on_iff_chunk(self, chunk):
        if chunk.typeid == self.__node_chunk_type:
            mtypeid = self._read_mtypeid()
            if mtypeid == MAYA:
                self._handle_all_chunks()
            elif mtypeid == HEAD:
                self._parse_maya_header()
            elif mtypeid == FREF:
                self._parse_file_reference()
            elif mtypeid == CONN:
                self._parse_connection()
            else:
                self._parse_node(mtypeid)

        elif chunk.typeid == self.__list_chunk_type:
            mtypeid = self._read_mtypeid()
            if mtypeid == CONS:
                self._handle_all_chunks()

    def _read_mtypeid(self):
        # 64-bit format still uses 32-bit MTypeIds
        result = be_read4(self.stream)
        self._realign()
        return result

    def _parse_maya_header(self):
        angle_unit = None
        linear_unit = None
        time_unit = None

        for chunk in self._iter_chunks():
            # requires (maya)
            if chunk.typeid == VERS:
                self.on_requires_maya(self._read_chunk_data(chunk))
            
            # requires (plugin)
            elif chunk.typeid == PLUG:
                plugin = read_null_terminated(self.stream)
                version = read_null_terminated(self.stream)
                self.on_requires_plugin(plugin, version)

            # fileInfo
            elif chunk.typeid == FINF:
                key = read_null_terminated(self.stream)
                value = read_null_terminated(self.stream)
                self.on_file_info(key, value)

            # on_current_unit callback is deferred until all three 
            # angle, linear and time units are read from the stream.

            # currentUnit (angle)
            elif chunk.typeid == AUNI:
                angle_unit = self._read_chunk_data(chunk)

            # currentUnit (linear)
            elif chunk.typeid == LUNI:
                linear_unit = self._read_chunk_data(chunk)

            # currentUnit (time)
            elif chunk.typeid == TUNI:
                time_unit = self._read_chunk_data(chunk)

            # Got all three units
            if angle_unit and linear_unit and time_unit:
                self.on_current_unit(angle=angle_unit,
                                     linear=linear_unit,
                                     time=time_unit)
                angle_unit = None
                linear_unit = None
                time_unit = None

        # Didn't get all three units (this is non standard)
        if angle_unit or linear_unit or time_unit:
            self.on_current_unit(angle=angle_unit,
                                 linear=linear_unit,
                                 time=time_unit)

    def _parse_file_reference(self):
        for chunk in self._iter_chunks(types=[FREF]):
            self.on_file_reference(read_null_terminated(self.stream))

    def _parse_connection(self):
        self.stream.read(17 if self.__maya64 else 9)
        src = read_null_terminated(self.stream)
        dst = read_null_terminated(self.stream)
        self.on_connect_attr(src, dst)

    def _parse_node(self, mtypeid):
        for chunk in self._iter_chunks():
            # Create node
            if chunk.typeid == CREA:
                typename = self.__mtypeid_to_typename.get(mtypeid, "unknown")
                name_parts = self._read_chunk_data(chunk)[1:-1].split("\0")
                name = name_parts[0]
                parent_name = name_parts[1] if len(name_parts) > 1 else None
                self.on_create_node(typename, name, parent=parent_name)

            # Select the current node
            elif chunk.typeid == SLCT:
                pass

            # Dynamic attribute
            elif chunk.typeid == ATTR:
                pass

            # Flags
            elif chunk.typeid == FLGS:
                pass

            # Set attribute
            else:
                self._parse_attribute(chunk.typeid)

    def _parse_attribute(self, mtypeid):
        # TODO Support more primitive types
        if mtypeid == STR_:
            self._parse_string_attribute()
        elif mtypeid == DBLE:
            self._parse_double_attribute()
        elif mtypeid == DBL3:
            self._parse_double3_attribute()
        else:
            self._parse_mpxdata_attribute(mtypeid)

    def _parse_attribute_info(self):
        attr_name = read_null_terminated(self.stream)
        mystery_flag = self.stream.read(1)
        count = plug_element_count(attr_name)
        return attr_name, count

    def _parse_string_attribute(self):
        attr_name, count = self._parse_attribute_info()
        value = read_null_terminated(self.stream)
        self.on_set_attr(attr_name, value, type="string")

    def _parse_double_attribute(self):
        attr_name, count = self._parse_attribute_info()
        value = struct.unpack(">" + "d" * count,
                              self.stream.read(8 * count))
        value = value[0] if count == 1 else value
        self.on_set_attr(attr_name, value, type="double")

    def _parse_double3_attribute(self):
        attr_name, count = self._parse_attribute_info()
        value = struct.unpack(">" + "ddd" * count,
                              self.stream.read(24 * count))
        self.on_set_attr(attr_name, value, type="double3")

    def _parse_mpxdata_attribute(self, tyepid):
        # TODO
        pass

    def _load_mtypeid_database(self, path):
        with open(path) as f:
            line = f.readline()
            while line:
                mtypeid = be_word4(line[:4])
                typename = line[5:].strip()
                self.__mtypeid_to_typename[mtypeid] = typename
                line = f.readline()
