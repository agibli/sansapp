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


# General
MAYA = be_word4("Maya")
FOR4 = be_word4("FOR4")
LIS4 = be_word4("LIS4")

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
                           alignment=4,
                           typeid_bytes=4,
                           size_bytes=4)


class MayaBinaryParser(IffParser):
    def __init__(self, stream):
        # TODO support 64-bit IFF files from Maya 2014+
        super(MayaBinaryParser, self).__init__(stream, format=MAYA_BINARY_32)

        # FIXME load type info modules based on maya and plugin versions
        self.__mtypeid_to_typename = {}
        self._load_mtypeid_database(os.path.join(os.path.dirname(__file__),
                                    "modules", "maya", "2012", "typeids.dat"))

    def on_iff_chunk(self, chunk):
        if chunk.typeid == FOR4:
            mtypeid = be_read4(self.stream)
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

        elif chunk.typeid == LIS4:
            mtypeid = be_read4(self.stream)
            if mtypeid == CONS:
                self._handle_all_chunks()

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
        self.stream.read(9)
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

    def on_requires_maya(self, version):
        pass

    def on_requires_plugin(self, plugin, version):
        pass

    def on_file_info(self, key, value):
        pass

    def on_current_unit(self, angle, linear, time):
        pass

    def on_file_reference(self, path):
        pass

    def on_create_node(self, nodetype, name, parent):
        pass

    def on_select(self, name):
        pass

    def on_add_attr(self, node, name):
        pass

    def on_set_attr(self, name, value, type):
        pass

    def on_set_attr_flags(self, plug, keyable=None, channelbox=None, lock=None):
        pass

    def on_connect_attr(self, src_plug, dst_plug):
        pass

    def _load_mtypeid_database(self, path):
        with open(path) as f:
            line = f.readline()
            while line:
                mtypeid = be_word4(line[:4])
                typename = line[5:].strip()
                self.__mtypeid_to_typename[mtypeid] = typename
                line = f.readline()