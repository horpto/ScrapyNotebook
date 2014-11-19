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
            tn = other.shell.ev(args.scrapy)
            del args.scrapy
            return tn
        if self.scrapy_required:
            raise ValueException('You should init or choose scrapy for a start')

    def print_exc(self, exc):
        print_err(exc)
        if self.debug:
            import traceback
            traceback.print_exc()

def get_value_in_context(obj, scrapy_side, shell):
    try:
        return scrapy_side.eval(obj)
    except:
        return shell.ev(obj)
