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
                                  is_valid_url,
                                  highlight_python_source,
                                  get_value_in_context,
                                  get_ipython_variables,
                                  transform_arguments as _transform_arguments,)
from ScrapyNotebook.utils.scrapy_utils import scrapy_embedding
from ScrapyNotebook.utils.rpyc_utils import (LoggableSocketStream, is_remote)
from ScrapyNotebook.scrapy_side import (LocalScrapy, RemoteScrapy, ScrapySide)
from ScrapyNotebook.utils.sources import get_source

import rpyc
import socket
import logging
logger = logging.getLogger()

from scrapy.spider import BaseSpider

debug = True

transform_arguments = lambda *args, **kwargs: \
    _transform_arguments(debug=debug, *args, **kwargs)

@magics_class
class ScrapyNotebook(Magics):
    # should be None, ScrapySide or set(ScrapySide)
    _scrapy_side = set()

    @classmethod
    def scrapy_side(cls):
        if len(cls._scrapy_side) == 1:
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

    @staticmethod
    def _get_connection(host, port):
        if debug:
            stream = LoggableSocketStream.connect(host, port)
            return rpyc.classic.connect_stream(stream)
        return rpyc.classic.connect(host, port)

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
            if args.spider is not None:
                args.spider = self.shell.ev(args.spider)
            if not is_valid_url(args.url) \
               and args.url is not None:
                    args.url = self.shell.ev(args.url)
            crawler = scrapy_embedding(args.spider, args.url)
            tn = LocalScrapy(self.shell, crawler)
            self.add_new_scrapy_side(tn)
            return tn
        except Exception as exc:
            print_err(exc)

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
                conn = self._get_connection(host, port)
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
            print_err(exc)

    @transform_arguments()
    @cell_magic
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

    @transform_arguments()
    @line_magic
    def stop_scrapy(self, tn, *args):
        '''Stop scrapy. At all.'''
        tn.stop_scrapy()
        self.delete_scrapy_side(tn)

    @transform_arguments()
    @line_magic
    def pause_scrapy(self, tn, *args):
        '''Pausing scrapy. To continue use %resume_scrapy'''
        tn.pause_scrapy()

    @transform_arguments()
    @line_magic
    def resume_scrapy(self, tn, *args):
        '''Continue crawling'''
        tn.resume_scrapy()

    @transform_arguments()
    @line_magic
    def common_stats(self, tn, *args):
        return tn.get_stats()

    @transform_arguments()
    @line_magic
    def spider_stats(self, tn, *args):
        return tn.spider_stats

    @transform_arguments(scrapy_required=False)
    @argument('arg')
    @line_magic
    def print_source(self, tn, args, line):
        '''Print(if can) source of method or function or class'''
        obj = get_value_in_context(args.arg, tn, self.shell)
        try:
            source = tn.get_source(obj) if is_remote(obj) else get_source(obj)
        except (TypeError, IOError) as exc:
            print "Error:", exc
            return
        display_html(highlight_python_source(source), raw=True)

    @transform_arguments(scrapy_required=False)
    @argument('object')
    @cell_magic
    def set_method(self, tn, args, line, cell):
        '''Change method some method
        Example:
        %%set_method MySpider.my_aswesome_method_name
        def some_method(self, arg):
            pass
        '''
        arg = args.object.strip()
        try:
            obj, method_name = arg.rsplit('.', 1)
        except ValueError:
            obj, method_name = arg.split()

        obj = get_value_in_context(obj, tn, self.shell)
        tn.set_method(obj, method_name, cell)

    @transform_arguments()
    @line_cell_magic
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
