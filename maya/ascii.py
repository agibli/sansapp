from common import *


class MayaAsciiError(ValueError):
    pass


class MayaAsciiParserBase(MayaParserBase):
    def __init__(self):
        self.__command_handlers = {
            "requires": self._exec_requires,
            "fileInfo": self._exec_file_info,
            "createNode": self._exec_create_node,
            "setAttr": self._exec_set_attr,
        }

    def on_comment(self, value):
        pass

    def register_handler(self, command, handler):
        self.__command_handlers[command] = handler

    def exec_command(self, command, args):
        handler = self.__command_handlers.get(command, None)
        if handler is not None:
            handler(args)

    def has_command(self, command):
        return command in self.__command_handlers

    def _exec_requires(self, args):
        if args[0] == "maya":
            self.on_requires_maya(args[1])
        else:
            self.on_requires_plugin(args[0], args[1])

    def _exec_file_info(self, args):
        self.on_file_info(args[0], args[1])

    def _exec_create_node(self, args):
        nodetype = args[0]

        name = None
        parent = None
        shared = False

        argptr = 1
        while argptr < len(args):
            arg = args[argptr]
            if arg in ("-n", "--name"):
                name = args[argptr + 1]
                argptr += 2
            elif arg in ("-p", "--parent"):
                parent = args[argptr + 1]
                argptr += 2
            elif arg in ("-s", "--shared"):
                shared = True
                argptr += 1
            else:
                raise MayaAsciiError, "Unexpected argument: %s" % arg

        self.on_create_node(nodetype, name, parent)

    def _exec_set_attr(self, args):
        pass


class MayaAsciiParser(MayaAsciiParserBase):

    def __init__(self, stream):
        super(MayaAsciiParser, self).__init__()
        self.__stream = stream

    def parse(self):
        while self.__parse_next_command():
            pass

    def __parse_next_command(self):
        lines = []

        line = self.__stream.readline()
        while True:
            # Check if we've reached the end of the file
            if not line:
                break

            # Handle comments
            elif line.startswith("//"):
                self.on_comment(line[2:].strip())

            # Handle commands
            # A command may span multiple lines
            else:
                line = line.rstrip("\r\n")
                if line and line.endswith(";"):
                    # Remove trailing semicolon here so the command line
                    # processor doesn't have to deal with it.
                    lines.append(line[:-1])
                    break
                elif line:
                    lines.append(line)
            line = self.__stream.readline()

        if lines:
            self.__parse_command_lines(lines)
            return True

        return False

    def __parse_command_lines(self, lines):
        # Pop command name from the first line
        command, _, lines[0] = lines[0].partition(" ")
        command = command.lstrip()

        # Only process arguments if we handle this command
        if self.has_command(command):

            # Tokenize arguments
            args = []
            for line in lines:
                while True:
                    line = line.strip()
                    if not line:
                        break

                    # Handle strings
                    if line[0] in "'\"":
                        string_delim = line[0]
                        escaped = False
                        string_end = len(line)

                        for i in range(1, len(line)):

                            # Check for end delimeter
                            if not escaped and line[i] == string_delim:
                                string_end = i
                                break

                            # Check for start of escape sequence
                            elif not escaped and line[i] == "\\":
                                escaped = True

                            # End escape sequence
                            else:
                                escaped = False

                        # Partition string argument from the remainder
                        # of the command line.
                        arg, line = line[1:string_end], line[string_end + 1:]

                    # Handle other arguments
                    # These, unlike strings, may be tokenized by whitespace
                    else:
                        arg, _, line = line.partition(" ")

                    args.append(arg)

            # Done tokenizing arguments, call command handler
            self.exec_command(command, args)
