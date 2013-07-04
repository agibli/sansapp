def plug_element_count(plug):
    lbracket = plug.rfind("[")
    if lbracket != -1:
        rbracket = plug.rfind("]")
        if rbracket != -1 and lbracket < rbracket:
            slicestr = plug[lbracket + 1:rbracket]
            bounds = slicestr.split(":")
            if len(bounds) > 1:
                return int(bounds[1]) - int(bounds[0]) + 1
    return 1


class MayaParserBase(object):

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
