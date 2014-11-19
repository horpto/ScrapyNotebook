#!/bin/env python
# -*- encoding: utf-8 -*-

import sys
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import HtmlFormatter

from IPython.core.magic_arguments import (argument, magic_arguments,
    parse_argstring)
from functools import wraps

def print_err(arg):
    print >> sys.stderr, arg

# one of answers from
#http://stackoverflow.com/questions/827557/how-do-you-validate-a-url-with-a-regular-expression-in-python
#
# you can suggest a better solution
def is_valid_url(url):
    import re
    regex = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url is not None and regex.search(url)

def highlight_python_source(source):
    formatter = HtmlFormatter()
    return '<style type="text/css">{}</style>{}'.format(
        formatter.get_style_defs('.highlight'),
        highlight(source, PythonLexer(), formatter))


def transform_arguments(f):
    # this deco should be first in chain(on top)
    @magic_arguments()
    @argument('-s', '--scrapy', type=str,
              help='which scrapy use')
    @wraps(f)
    def func(self, line, cell=None):
        args = parse_argstring(getattr(self, f.__name__), line)

        tn = self.scrapy_side()
        if tn is None:
            if args.scrapy is None:
                msg = 'You should init or choose scrapy for a start'
                print_err(msg)
                return
            tn = self.shell.ev(args.scrapy)
            del args.scrapy
        try:
            if cell is None:
                return f(self, tn, args, line)
            return f(self, tn, args, line, cell)
        except Exception as exc:
            print_err(exc)
            if debug:
                import traceback
                traceback.print_exc()
    return func

class transform_arguments(object):

    def __init__(self, name=None, scrapy_required=True, debug=False):
        self.name = name
        self.debug = debug
        self.scrapy_required = scrapy_required
        self.func = None

    def __call__(self, func):
        self.func = func
        self.name = self.name or func.__name__

        @magic_arguments()
        @argument('-s', '--scrapy', help='which scrapy use')
        @wraps(func)
        def function(other, line, cell=None):
            args = parse_argstring(getattr(other, self.name), line)
            tn = self.get_scrapy_side(other, args)

            try:
                if cell is None:
                    return self.func(other, tn, args, line)
                return self.func(other, tn, args, line, cell)
            except Exception as exc:
                self.print_exc(exc)
        return function

    def get_scrapy_side(self, other, args):
        tn = other.scrapy_side()
        if tn is not None:
            return tn
        if args.scrapy is not None:
            tn = self.shell.ev(args.scrapy)
            del args.scrapy
            return tn
        if self.scrapy_required:
            print_err('You should init or choose scrapy for a start')

    def print_exc(self):
        print_err(exc)
        if self.debug:
            import traceback
            traceback.print_exc()
