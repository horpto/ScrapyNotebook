#! /usr/bin/python
# -*- coding: utf-8 -*-

from IPython.core.magic import (Magics, magics_class,
    line_magic, line_cell_magic, cell_magic)

from IPython.core.magic_arguments import (argument, magic_arguments,
    parse_argstring)
from IPython.display import display_html

from tornado.platform.twisted import install
try:
    install()
except:
    pass
    # ToDo: check if twisted installed right

from ScrapyNotebook.utils import (print_err,
                                  highlight_python_source,
                                 )
from ScrapyNotebook.utils.ipython_utils import (get_url_from_ipython,
                                                get_ipython_variables,
                                                get_value_in_context,
                                               )
from ScrapyNotebook.utils.scrapy_utils import (get_spidercls,
                                            scrapy_embedding,
                                            IPythonNotebookShell,)
from ScrapyNotebook.utils.rpyc_utils import (get_rpyc_connection, is_remote)
from ScrapyNotebook.scrapy_side import (LocalScrapy,
                                        RemoteScrapy,
                                        ScrapySideStore,
                                       )
from ScrapyNotebook.utils.sources import get_source, split_on_last_method

import socket
import logging
logger = logging.getLogger()

debug = True
from functools import wraps


class transform_arguments(object):

    def __init__(self, name=None, scrapy_required=True, magic_type=line_magic):
        self.name = name
        self.scrapy_required = scrapy_required
        self.func = None
        self.magic_type = magic_type

    def __call__(self, func):
        self.func = self.magic_type(func)
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
            side = self.get_scrapy_side(other, args)

            if cell is None:
                return self.func(other, side, args, line)
            return self.func(other, side, args, line, cell)
        except Exception as exc:
            print_err(exc, debug=debug)

    def get_scrapy_side(self, other, args):
        side = other._scrapy_sides.scrapy_side
        if side is not None:
            return side
        if args.scrapy is not None:
            side = other.shell.ev(args.scrapy)
            del args.scrapy
            return side
        if self.scrapy_required:
            raise ValueError('You should init or choose scrapy for a start')


@magics_class
class ScrapyNotebook(Magics):
    _scrapy_sides = ScrapySideStore()

    @line_magic
    def scrapy_list(self, line):
        'show all available scrapies'
        if self._scrapy_sides.scrapy_side:
            return list(self._scrapy_sides)
        print('No scrapies')
        return []

    def add_new_scrapy_side(self, scrapy_side):
        self._scrapy_sides.scrapy_side = scrapy_side
        variables = scrapy_side.namespace
        if variables:
            self.shell.push(variables)
            print("Variables are loaded: {}".format(', '.join(variables)))

    @magic_arguments()
    @argument(
        '-s', '--spidercls', help='spider class for scrapy'
    )
    @argument(
        '-u', '--url', help='start url-page'
    )
    @line_magic
    def scrapy_embed(self, arg):
        try:
            args = parse_argstring(self.scrapy_embed, arg)
            url = get_url_from_ipython(args.url, self.shell)
            spidercls = self._parse_spidercls(args.spidercls, url)

            crawler = scrapy_embedding(spidercls)

            scrapy_shell = IPythonNotebookShell(self.shell, crawler)
            scrapy_shell.start(url=url)
            side = LocalScrapy(self.shell, crawler)
            # FIXME: request and response vars push later so they are not printed as loaded
            self.add_new_scrapy_side(side)
            return side
        except Exception as exc:
            print_err(exc, debug=debug)

    def _parse_spidercls(self, spidercls, url):
        if spidercls is not None:
            spidercls = self.shell.ev(spidercls)
            # spider is not a variable or expression
        return get_spidercls(spidercls, url)

    @magic_arguments()
    @argument(
        '-h', '--host', type=str, default='localhost',
        help='remote host'
    )
    @argument(
        '-p', '--port', type=int, default=13113,
        help='host port'
    )
    @line_magic
    def scrapy_attach(self, arg):
        try:
            args = parse_argstring(self.scrapy_attach, arg)
            host, port = args.host, args.port
            assert 1 <= port <= 65536

            try:
                conn = get_rpyc_connection(host, port, debug)
            except socket.gaierror:
                print_err("Wrong host: " + host)
                return
            except socket.error:
                print_err("Connection failure")
                return

            side = RemoteScrapy(self.shell, conn)
            self.add_new_scrapy_side(side)
            return side
        except Exception as exc:
            print_err(exc, debug=debug)

    @transform_arguments(magic_type=cell_magic)
    def process_shell(self, side, args, line, source):
        '''Execute code on scrapy side.
        Dangerous if code is IO blocking or has infinite loop'''
        namespace = get_ipython_variables(self.shell)
        side.push_variables(namespace)
        res = side.execute(source)

        # remove difference of local and remote namespaces
        side.repair_namespace()
        return res

    @transform_arguments(magic_type=line_magic)
    def scrapy_stop(self, side, *args):
        '''Stop scrapy. At all.'''
        side.stop_scrapy()
        self._scrap_sides.delete(side)

    @transform_arguments(magic_type=line_magic)
    def scrapy_pause(self, side, *args):
        '''Pausing scrapy. To continue use %resume_scrapy'''
        side.pause_scrapy()

    @transform_arguments(magic_type=line_magic)
    def scrapy_resume(self, side, *args):
        '''Continue crawling'''
        side.resume_scrapy()

    @transform_arguments(magic_type=line_magic)
    def common_stats(self, side, *args):
        return side.get_stats()

    @transform_arguments(magic_type=line_magic)
    def spider_stats(self, side, *args):
        return side.spider_stats

    @transform_arguments(scrapy_required=False, magic_type=line_magic)
    @argument('arg')
    def print_source(self, side, args, line):
        '''Print(if can) source of method or function or class'''
        obj = get_value_in_context(args.arg, side, self.shell)
        try:
            source = side.get_source(obj) if is_remote(obj) else get_source(obj)
        except (TypeError, IOError) as exc:
            print_err(exc, debug=debug)
            return
        display_html(highlight_python_source(source), raw=True)

    @transform_arguments(scrapy_required=False, magic_type=cell_magic)
    @argument('object')
    def set_method(self, side, args, line, cell):
        '''Change method some method
        Example:
        %%set_method MySpider.my_aswesome_method_name
        def some_method(self, arg):
            pass
        '''
        obj, method_name = split_on_last_method(args)
        obj = get_value_in_context(obj, side, self.shell)
        side.set_method(obj, method_name, cell)

    @transform_arguments(magic_type=line_cell_magic)
    def scrapy_visualize(self, side, *args):
        '''not Implemented'''
        side.visualize_scrapy()


_loaded = False

def load_ipython_extension(ip):
    global _loaded
    if _loaded:
        return
    _loaded = True
    ip.register_magics(ScrapyNotebook)
    logger.debug("Loaded")

def unload_ipython_extension(ip):
    ScrapyNotebook._scrapy_sides.delete_all()
    logger.debug("Unload")
