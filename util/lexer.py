import re
import mmap
from collections import namedtuple


Rule = namedtuple("Rule", ["name", "regex"])
Token = namedtuple("Token", ["pos", "rule", "value"])


class LexerError(ValueError):
    pass


class LexerRules(object):

    Ident = Rule("IDENT", r"[a-zA-Z_][a-zA-Z0-9_]*")
    Whitespace = Rule("SPACE", r"\s+")
    DecInt = Rule("DECINT", r"[+-]?[1-9][0-9]*")
    OctInt = Rule("OCTINT", r"[+-]?0[0-7]*")
    HexInt = Rule("HEXINT", r"[+-]?0x[0-9A-F]+")
    String = Rule("STRING", r'"(?:\\.|[^\\"\r\n])*"')
    SingleQuoteString = Rule("SQSTR", r"'(?:\\.|[^\\'\r\n])*'")

    CLineComment = Rule(name="LINCMT", regex=r"//.+")
    CBlockComment = Rule(name="BLKCMT", regex=r"/\*[^*]*\*+(?:[^*/][^*]*\*+)*/")

    ShEval = Rule("SHEVAL", r"`(?:\\.|[^\\`\r\n])*`")
    ShLongArg = Rule("SHLONG", r"--[a-zA-Z]+[\w-]*")
    ShShortArg = Rule("SHSHRT", r"-[a-zA-Z]+")

    Semicolon = Rule(name="SEMCOL", regex=r";")


class SimpleLexer(object):
    def __init__(self, stream, rules=None, mmapped=True):
        rules = rules or []
        self.__stream = stream
        self.__rules = rules[:]
        self.__rule_dict = dict((r.name, r) for r in rules)
        self.__regex = re.compile("")
        self.__update_regex()
        self.__pos = 0

        if mmapped and hasattr(self.__stream, "fileno"):
            self.__input = mmap.mmap(self.__stream.fileno(), 0, prot=mmap.PROT_READ)
            self.__input_end = self.__input.size()
            self.__advance_line = self.__advance_line_mmapped
        else:
            # Temporary workaround for non-file streams.
            self.__input = stream.read()
            self.__input_end = len(self.__input)

    def append_rule(self, rule):
        self.__rules.append(rule)
        self.__rule_dict[rule.name] = rule
        self.__update_regex()

    def read_token(self):
        if self.__pos >= self.__input_end:
            return None

        match = self.__regex.match(self.__input, self.__pos)
        if match is None:
            raise LexerError, "Input stream contains unexpected characters."

        value = match.group()
        if not value:
            raise LexerError, "Grammar matched an empty string."

        rule = self.__rule_dict.get(match.lastgroup)
        if rule is None:
            raise LexerError, "Input stream matched an unknown rule."

        start, end = match.span()

        self.__pos = end

        return Token(pos=start, rule=rule, value=value)

    def __update_regex(self):
        to_named_group = lambda r: "(?P<%s>%s)" % (r.name, r.regex)
        regex = "|".join(map(to_named_group, self.__rules))
        self.__regex = re.compile(regex)
