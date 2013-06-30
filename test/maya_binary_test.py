import sys
from sansapp.maya import MayaBinaryParser


class TestMayaBinaryParser(MayaBinaryParser):

    def on_requires_maya(self, version):
        print "Maya Version: %s" % version

    def on_requires_plugin(self, plugin, version):
        print "Requires Plugin: %s %s" % (plugin, version)

    def on_file_info(self, key, value):
        print "File Info [%16s]: %s" % (key, value)

    def on_current_unit(self, angle, linear, time):
        print "Units: Angle=%s Linear=%s Time=%s" % (angle, linear, time)

    def on_file_reference(self, path):
        print "Reference: %s" % path

    def on_create_node(self, nodetype, name, parent):
        print "Create Node: Type=%s Name=%s Parent=%s" % (nodetype, name, parent)

    def on_set_attr(self, name, value, type):
        print "Set Attribute: [%s] %s=%s" % (type, name, repr(value))


test = TestMayaBinaryParser(stream=open(sys.argv[1], "rb"))
test.parse()
