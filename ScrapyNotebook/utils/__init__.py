#!/bin/env python
# -*- encoding: utf-8 -*-

import sys
from types import TypeType, ClassType
try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter
    pygments_plugin = True
except ImportError:
    pygments_plugin = False

from IPython.core.magic_arguments import (argument, magic_arguments,
    parse_argstring)
from functools import wraps

def print_err(arg, debug=False):
    print >> sys.stderr, arg
    if debug:
        import traceback
        traceback.print_exc()

# one of answers from
#http://stackoverflow.com/questions/827557/how-do-you-validate-a-url-with-a-regular-expression-in-python
#
# you can suggest a better solution
def is_valid_url(url):
    import re
    regex = re.compile(
        r'(^https?://)?'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url is not None and regex.search(url)

def highlight_python_source(source):
    if not pygments_plugin:
        return '<pre><code>{}</code></pre'.format(source)
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
        def _func(*args, **kwargs):
            self.deco_body(*args, **kwargs)
        return _func

    def deco_body(self, other, line, cell=None):
        args = parse_argstring(getattr(other, self.name), line)

        try:
            tn = self.get_scrapy_side(other, args)

            if cell is None:
                return self.func(other, tn, args, line)
            return self.func(other, tn, args, line, cell)
        except Exception as exc:
            self.print_exc(exc)

    def get_scrapy_side(self, other, args):
        tn = other.scrapy_side()
        if tn is not None:
            return tn
        if args.scrapy is not None:
            tn = other.shell.ev(args.scrapy)
            del args.scrapy
            return tn
        if self.scrapy_required:
            raise ValueError('You should init or choose scrapy for a start')

def get_value_in_context(obj, scrapy_side, shell):
    try:
        return scrapy_side.eval(obj)
    except:
        return shell.ev(obj)


def get_ipython_variables(shell):
    who_ls = shell.find_line_magic('who_ls')
    return {var: shell.ev(var) for var in who_ls()}

def is_typeobj(obj):
    return isinstance(obj, (TypeType, ClassType))

def get_url_from_ipython(url, shell):
    if not is_valid_url(url) and url is not None:
        url = shell.ev(url)
    return url
