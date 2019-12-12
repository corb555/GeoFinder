import argparse

# Variant of ArgParse which will not exit when there is a parser error, instead raises exception
class ArgumentParserError(Exception): pass

class ArgumentParserNoExit(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)