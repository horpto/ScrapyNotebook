#!/bin/env python
# -*- encoding: utf-8 -*-

import sys
import cgi
from types import TypeType, ClassType

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter
    pygments_plugin = True
except ImportError:
    pygments_plugin = False

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

def escape_html(text):
    """escape strings for display in HTML"""
    return cgi.escape(text, quote=True).\
           replace(u'\n', u'<br />').\
           replace(u'\t', u'&emsp;').\
           replace(u'  ', u' &nbsp;')

def highlight_python_source(source):
    if not pygments_plugin:
        return '<pre><code>{}</code></pre'.format(source)
    formatter = HtmlFormatter()
    return '<style type="text/css">{}</style>{}'.format(
        formatter.get_style_defs('.highlight'),
        highlight(source, PythonLexer(), formatter))

def is_typeobj(obj):
    return isinstance(obj, (TypeType, ClassType))

