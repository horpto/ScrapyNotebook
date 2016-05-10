#! /usr/bin/python
# -*- coding: utf-8 -*-
"""
Created on Sat Mar 01 20:15:47 2014

@author: Александр
"""
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
                                  get_url_from_ipython,
                                  highlight_python_source,
                                  get_value_in_context,
                                  get_ipython_variables,
                                 )
from ScrapyNotebook.utils.scrapy_utils import (get_spider,
                                            scrapy_embedding,
                                            IPythonNotebookShell,)
from ScrapyNotebook.utils.rpyc_utils import (LoggableSocketStream, is_remote)
from ScrapyNotebook.scrapy_side import (LocalScrapy, RemoteScrapy, ScrapySide)
from ScrapyNotebook.utils.sources import get_source, split_on_last_method

import rpyc
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
            tn = self.get_scrapy_side(other, args)

            if cell is None:
                return self.func(other, tn, args, line)
            return self.func(other, tn, args, line, cell)
        except Exception as exc:
            print_err(exc, debug=debug)

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


def get_rpyc_connection(host, port):
    if debug:
        stream = LoggableSocketStream.connect(host, port)
        return rpyc.classic.connect_stream(stream)
    return rpyc.classic.connect(host, port)


@magics_class
class ScrapyNotebook(Magics):
    # should be None, ScrapySide or set(ScrapySide)
    _scrapy_side = set()

    @classmethod
    def scrapy_side(cls):
        if len(cls._scrapy_side) != 1:
            return
        # return the only remaining scrapy side
        for side in cls._scrapy_side:
            return side

    @classmethod
    def set_scrapy_side(cls, new_value):
        if not isinstance(new_value, ScrapySide):
            raise TypeError('%s should be ScrapySide instance' % new_value)
        cls._scrapy_side.add(new_value)

    @classmethod
    def delete_scrapy_side(cls, scrapy_side=None):
        if scrapy_side is None:
            del cls._scrapy_side
            cls._scrapy_side = set()
            return
        if not isinstance(scrapy_side, ScrapySide):
            raise TypeError('%s should be ScrapySide instance' % scrapy_side)
        #  удаляем только этот скрепи
        cls._scrapy_side.discard(scrapy_side)
        del scrapy_side

    @line_magic
    def scrapy_list(self, line):
        'show all available scrapies'
        tn = self._scrapy_side
        if tn:
            return list(tn)
        print 'No scrapies'
        return []


    def add_new_scrapy_side(self, scrapy_side):
        self.set_scrapy_side(scrapy_side)
        variables = scrapy_side.namespace
        if variables:
            self.shell.push(variables)
            print("Variables are loaded: {}".format(', '.join(variables)))

    @magic_arguments()
    @argument(
        '-s', '--spider', help='spider for scrapy'
    )
    @argument(
        '-u', '--url', help='start url-page'
    )
    @line_magic
    def embed_scrapy(self, arg):
        try:
            args = parse_argstring(self.embed_scrapy, arg)
            url = get_url_from_ipython(args.url, self.shell)

            spider = self._parse_spider(args.spider, url)
            crawler = scrapy_embedding(url=url, spider=spider)

            shell = IPythonNotebookShell(self.shell, crawler)
            shell.start(url=url, spider=spider)
            tn = LocalScrapy(self.shell, crawler)
            self.add_new_scrapy_side(tn)
            return tn
        except Exception as exc:
            print_err(exc, debug=debug)

    def _parse_spider(self, spider, url):
        if spider is not None:
            try:
                spider = self.shell.ev(spider)
            except Exception as exc:
                print_err('Spider is None now')
                print_err(exc, debug=debug)
                # spider is not a variable or expression
        return get_spider(spider, url)

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
    def attach_scrapy(self, arg):
        try:
            args = parse_argstring(self.attach_scrapy, arg)
            host, port = args.host, args.port
            assert 1 <= port <= 65536

            try:
                conn = get_rpyc_connection(host, port)
            except socket.gaierror:
                print_err("Wrong host: " + host)
                return
            except socket.error:
                print_err("Connection failure")
                return

            tn = RemoteScrapy(self.shell, conn)
            self.add_new_scrapy_side(tn)
            return tn
        except Exception as exc:
            print_err(exc, debug=debug)

    @transform_arguments(magic_type=cell_magic)
    def process_shell(self, tn, args, line, source):
        '''Execute code on scrapy side.
        Dangerous if code is IO blocking or has infinite loop'''
        namespace = get_ipython_variables(self.shell)
        tn.push_variables(namespace)

        res = tn.execute(source)

        # remove difference of local and remote namespaces
        keys = tn.get_keys
        for i in tn.keys - keys:
            self.shell.remove(i)
        tn.keys = keys
        self.shell.push(tn.namespace)
        return res

    @transform_arguments(magic_type=line_magic)
    def stop_scrapy(self, tn, *args):
        '''Stop scrapy. At all.'''
        tn.stop_scrapy()
        self.delete_scrapy_side(tn)

    @transform_arguments(magic_type=line_magic)
    def pause_scrapy(self, tn, *args):
        '''Pausing scrapy. To continue use %resume_scrapy'''
        tn.pause_scrapy()

    @transform_arguments(magic_type=line_magic)
    def resume_scrapy(self, tn, *args):
        '''Continue crawling'''
        tn.resume_scrapy()

    @transform_arguments(magic_type=line_magic)
    def common_stats(self, tn, *args):
        return tn.get_stats()

    @transform_arguments(magic_type=line_magic)
    def spider_stats(self, tn, *args):
        return tn.spider_stats

    @transform_arguments(scrapy_required=False, magic_type=line_magic)
    @argument('arg')
    def print_source(self, tn, args, line):
        '''Print(if can) source of method or function or class'''
        obj = get_value_in_context(args.arg, tn, self.shell)
        try:
            source = tn.get_source(obj) if is_remote(obj) else get_source(obj)
        except (TypeError, IOError) as exc:
            print_err(exc, debug=debug)
            return
        display_html(highlight_python_source(source), raw=True)

    @transform_arguments(scrapy_required=False, magic_type=cell_magic)
    @argument('object')
    def set_method(self, tn, args, line, cell):
        '''Change method some method
        Example:
        %%set_method MySpider.my_aswesome_method_name
        def some_method(self, arg):
            pass
        '''
        obj, method_name = split_on_last_method(args)
        obj = get_value_in_context(obj, tn, self.shell)
        tn.set_method(obj, method_name, cell)

    @transform_arguments(magic_type=line_cell_magic)
    def visualize_scrapy(self, tn, *args):
        '''not Implemented'''
        tn.visualize_scrapy()


_loaded = False

def load_ipython_extension(ip):
    global _loaded
    if _loaded:
        return
    _loaded = True
    ip.register_magics(ScrapyNotebook)
    logger.debug("Loaded")

def unload_ipython_extension(ip):
    ScrapyNotebook.delete_scrapy_side()
    logger.debug("Unload")
