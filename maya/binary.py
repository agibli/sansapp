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
        self.__mtypeid_to_typename = {}

        # FIXME load type info modules based on maya and plugin versions
        self._load_mtypeid_database(os.path.join(os.path.dirname(__file__),
                                    "modules", "maya", "2012", "typeids.dat"))

    def on_iff_chunk(self, chunk):
        if chunk.typeid == FOR4:
            element_type = be_read4(self.stream)

            if element_type == MAYA:
                self._handle_all_chunks()
        
            # Parse header
            elif element_type == HEAD:

                angle_unit = None
                linear_unit = None
                time_unit = None

                for head_chunk in self._iter_chunks():

                    # requires (maya)
                    if head_chunk.typeid == VERS:
                        self.on_requires_maya(self._read_chunk_data(head_chunk))
                    
                    # requires (plugin)
                    elif head_chunk.typeid == PLUG:
                        plugin = read_null_terminated(self.stream)
                        version = read_null_terminated(self.stream)
                        self.on_requires_plugin(plugin, version)

                    # fileInfo
                    elif head_chunk.typeid == FINF:
                        key = read_null_terminated(self.stream)
                        value = read_null_terminated(self.stream)
                        self.on_file_info(key, value)

                    # on_current_unit callback is deferred until all three 
                    # angle, linear and time units are read from the stream.

                    # currentUnit (angle)
                    elif head_chunk.typeid == AUNI:
                        angle_unit = self._read_chunk_data(head_chunk)

                    # currentUnit (linear)
                    elif head_chunk.typeid == LUNI:
                        linear_unit = self._read_chunk_data(head_chunk)

                    # currentUnit (time)
                    elif head_chunk.typeid == TUNI:
                        time_unit = self._read_chunk_data(head_chunk)

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

            # Parse file references
            elif element_type == FREF:
                for chunk in self._iter_chunks(types=[FREF]):
                    self.on_file_reference(read_null_terminated(self.stream))

            # Modify builtin node
            elif element_type == SLCT:
                pass

            else:
                for child_chunk in self._iter_chunks():

                    # Create node
                    if child_chunk.typeid == CREA:
                        typename = self.__mtypeid_to_typename.get(element_type, "unknown")
                        name_parts = self._read_chunk_data(child_chunk)[1:-1].split("\0")
                        name = name_parts[0]
                        parent_name = name_parts[1] if len(name_parts) > 1 else None
                        self.on_create_node(typename, name, parent=parent_name)

                    # Dynamic attribute
                    elif child_chunk.typeid == ATTR:
                        pass

                    # String value
                    elif child_chunk.typeid == STR_:
                        attr_name = read_null_terminated(self.stream)
                        self.stream.read(1)
                        value = read_null_terminated(self.stream)
                        self.on_set_attr(attr_name, value, type="string")

                    elif child_chunk.typeid == DBLE:
                        attr_name = read_null_terminated(self.stream)
                        count = plug_element_count(attr_name)
                        self.stream.read(1)
                        value = struct.unpack(">" + "d" * count, self.stream.read(8 * count))
                        value = value[0] if count == 1 else value
                        self.on_set_attr(attr_name, value, type="double")

                    elif child_chunk.typeid == DBL3:
                        attr_name = read_null_terminated(self.stream)
                        self.stream.read(1)
                        value = struct.unpack(">ddd", self.stream.read(24))
                        self.on_set_attr(attr_name, value, type="double3")

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

    def on_connect_attr(self, src_plug, dst_plug, next_available):
        pass

    def _load_mtypeid_database(self, path):
        with open(path) as f:
            line = f.readline()
            while line:
                mtypeid = be_word4(line[:4])
                typename = line[5:].strip()
                self.__mtypeid_to_typename[mtypeid] = typename
                line = f.readline()
