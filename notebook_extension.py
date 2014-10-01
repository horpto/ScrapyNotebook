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

from tornado.platform.twisted import install
try:
    install()
except:
    pass
    # ToDo: check if twisted installed right

from ScrapyNotebook.utils import (LoggableSocketStream,
                                  scrapy_embedding,
                                  print_err)
from ScrapyNotebook.scrapy_side import (LocalScrapy, RemoteScrapy, ScrapySide)

import rpyc
import socket
from functools import wraps
import logging
logger = logging.getLogger()

from scrapy.spider import BaseSpider

@magics_class
class ScrapyNotebook(Magics):
    # should be None, ScrapySide or set(ScrapySide)
    _scrapy_side = set()
    
    @classmethod
    def scrapy_side(cls):
        if len(cls._scrapy_side) == 1:
            return cls._scrapy_side.pop()

    @classmethod
    def set_scrapy_side(cls, new_value):
        if not isinstance(new_value, ScrapySide):
            msg = '%s should be ScrapySide instance' % new_value
            print_err(msg)
            raise TypeError(msg)
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
        if self._scrapy_side:
            return list(self._scrapy_side)
        print 'No scrapies'

    @staticmethod
    def _get_connection(host, port):
        if logger.getEffectiveLevel <= logging.DEBUG:
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
        '-s', '--spider', type=BaseSpider,
        default=None,
        help='spider for scrapy'
    )
    @argument(
        '-u', '--url', type=unicode,
        help='start url-page'
    )
    @line_magic
    def embed_scrapy(self, arg):
        args = parse_argstring(self.embed_scrapy, arg)

        crawler = scrapy_embedding(args.spider, args.url)
        tn = LocalScrapy(self.shell, crawler)
        self.add_new_scrapy_side(tn)
        return tn

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
        args = parse_argstring(self.attach_scrapy, arg)
        host, port = args.host, args.port
        assert 1 <= port <= 65536

        try:
            conn = self._get_connection(host, port)
        except socket.gaierror:
            msg = "Wrong host: " + str(host)
            print_err(msg)
            raise ValueError(msg)
        except socket.error:
            print_err("Connection failure")
            raise EOFError("Connection failure")

        tn = RemoteScrapy(self.shell, conn)
        self.add_new_scrapy_side(tn)
        return tn

    def transform_arguments(f):
        #should be last
        @magic_arguments()
        @argument( '--scrapy', type=ScrapySide, default=None,
                  help='which scrapy use')
        @wraps(f)
        def func(self, arg):
            args = parse_argstring(getattr(self, f.__name__), arg)

            tn = self.scrapy_side()
            if tn is None:
                if args.scrapy is None:
                    msg = 'You should init or choose scrapy for a start'
                    print_err(msg)
                    raise IndexError(msg)
                tn = self.shell.ev(args.scrapy)
            return f(self, tn, args)
        return func

    @transform_arguments
    @line_cell_magic
    def process_shell(self, tn, args, source=None):
        '''Execute code on scrapy side.
        Dangerous if code is IO blocking or has infinite loop'''
        if source is None:
            source = args
        else:
            source = args + '\n' + source
        res = tn.execute(source)

        keys = tn.get_keys()
        for i in tn.keys - keys:
            self.shell.remove(i)
        tn.keys = keys
        self.shell.push(tn.namespace)
        return res

    @transform_arguments
    @line_magic
    def stop_scrapy(self, tn, args):
        '''Stop scrapy. At all.'''
        tn.stop_scrapy()
        self.delete_scrapy_side(tn)

    @transform_arguments
    @line_magic
    def pause_scrapy(self, tn, *args):
        '''Pausing scrapy. To continue use %resume_scrapy'''
        tn.pause_scrapy()

    @transform_arguments
    @line_magic
    def resume_scrapy(self, tn, *args):
        '''Continue scraping'''
        tn.resume_scrapy()

    @transform_arguments
    @line_magic
    def common_stats(self, tn, *args):
        return tn.get_stats()

    @transform_arguments
    @line_magic
    def spider_stats(self, tn, *args):
        return tn.spider_stats

    @transform_arguments
    @line_magic
    def print_source(self, tn, args):
        '''Print(is can) source of method or function or class'''
        obj = self.shell.ev(args)
        try:
            print(tn.get_source(obj))
        except (TypeError, IOError) as exc:
            print "Error:", exc

    @transform_arguments
    @cell_magic
    def set_method(self, tn, arg, text):
        '''Change method some method
        Example:
        %%set_method MySpider my_aswesome_method_name
        def some_method(self, arg):
            pass
        '''
        arg = arg.strip()
        try:
            splitted = arg.split()
        except ValueError:
            splitted = arg.rsplit('.', 1)
        obj, method_name = splitted

        obj = self.shell.ev(obj)
        tn.set_method(obj, method_name, text)

    @transform_arguments
    @line_cell_magic
    def visualize_scrapy(self, tn, *args):
        '''not Implemented'''
        tn.visualize_scrapy()

    # DELETING EXCESS
    del transform_arguments


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
