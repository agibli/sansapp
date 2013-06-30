def plug_element_count(plug):
    lbracket = plug.rfind("[")
    rbracket = plug.rfind("]")
    if lbracket != -1 and rbracket != -1 and lbracket < rbracket:
        slicestr = plug[lbracket + 1:rbracket]
        bounds = slicestr.split(":")
        if len(bounds) == 1:
            return 1
        else:
            return int(bounds[1]) - int(bounds[0]) + 1
    return 1