import argparse


class ArgumentParserError(Exception): pass

class ArgumentParserNoExit(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)