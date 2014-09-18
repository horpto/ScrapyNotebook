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

import logging
logger = logging.getLogger()

import rpyc
from rpyc.core.stream import SocketStream

import socket
import inspect

tn = None
_loaded = False


class LoggableSocketStream(SocketStream):

    def read(self, count):
        buf = SocketStream.read(self, count)
        logger.debug("Read: {}{}".format(buf, self.get_ending(buf)))
        return buf

    def write(self, data):
        logger.debug("Write: {}{}".format(data, self.get_ending(data)))
        SocketStream.write(self, data)

    @staticmethod
    def get_ending(buf):
        return '' if buf.endswith('\n') else '\n'


###############################################################################
###############################################################################


from tornado.platform.twisted import install
try:
    install()
except:
    pass
    # ToDo: check if twisted installed right

from scrapy.spider import BaseSpider
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin

class EarphoneBaseSpider(BaseSpider):
    name = u'e96_base'
    allowed_domains = [u'e96.ru']
    start_urls =[u'http://e96.ru/']
    
    def parse(self, response):
        sel = Selector(response)
        for req in self.find_links(response, sel):
            yield req

    def find_links(self, response, sel):
        url, base_url = response.url, get_base_url(response)

        for link in sel.xpath(u'//a/@href').extract():
            if self.is_file(link) or self.is_unnecessary(link):
                continue
            full_link = urljoin(base_url, link)
            yield Request(url=full_link)

    def is_file(self, url):
        return '.' in url.rpartition('/')[-1]

    def is_unnecessary(self, url):
        return not self.is_right_url(url) or self.is_get_request(url)

    def is_right_url(self, url):
        return url.startswith("/") or url.startswith('http')

    def is_get_request(self, url):
        return '?' in url


###############################################################################
###############################################################################

class ServerSide(object):
    builtins = set(('__builtin__', ))

    def __init__(self, conn, shell):
        self.closed = False
        self.conn = conn
        self.shell = shell
        self.namespace = self.conn.namespace
        self.keys = self.get_keys()
        self.redir = rpyc.classic.redirected_stdio(self.conn)
        
        stats = self.namespace['stats']
        self.get_stats = stats.get_stats
        self.spider_stats = stats.spider_stats
        self.engine = self.namespace['engine']

    def __del__(self):
        self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            self.redir.restore()
        except EOFError:
            pass
        finally:
            self.conn.close()

    def stop_scrapy(self):
        self.engine.stop()

    def pause_scrapy(self):
        self.engine.pause()

    def resume_scrapy(self):
        self.engine.unpause()

    def get_vars(self):
        return self.namespace

    def get_keys(self):
        keys = set(self.namespace.keys()) - self.builtins
        return keys

    def eval(self, line):
        self.conn.eval(line)

    def execute(self, text):
        self.conn.execute(text)

        try:
            del self.conn.namespace['__builtins__']
        except KeyError:
            pass

    def is_remote(self, obj):
        return isinstance(obj, (rpyc.core.netref.BaseNetref,
                                rpyc.core.netref.NetrefMetaclass))

    def get_source(self, obj):
        if self.is_remote(obj):
            getsource = self.conn.root.get_source
            type = lambda x: x.__class__
        else:
            getsource = inspect.getsource

        try:
            # if obj is module/class/method/function/etc.
            res = getsource(obj)
        except TypeError as exc:
            try:
                # else source of class
                res = getsource(type(obj))
            except:
                raise exc
        return res

    def set_method(self, obj, method_name, text):
        self.conn.root.set_source(obj, method_name, text)


###############################################################################
###############################################################################


@magics_class
class ScrapyNotebook(Magics):


    @staticmethod    
    def _get_connection(host, port):
        if logger.getEffectiveLevel <= logging.DEBUG:
            stream = LoggableSocketStream.connect(host, port)
            return rpyc.classic.connect_stream(stream)
        return rpyc.classic.connect(host, port)

    @magic_arguments()
    @argument('-o', '--option', help='An optional argument.')
    @argument('arg', type=int, help='An integer positional argument.')
    @line_magic
    def magic_cool(self, arg):
        args = parse_argstring(self.magic_cool, arg)
        return args

    @magic_arguments()
    @argument(
        '-s', '--spider', type=str, nargs='?',  default='',
        help=''
    )
    @argument(
        '-u', '--url', type=unicode,
    )
    @line_magic
    def embed_scrapy(self, arg):
        from scrapy.crawler import Crawler
        from scrapy import log, signals
        from scrapy.utils.project import get_project_settings
        from twisted.internet import reactor
        
        spider = EarphoneBaseSpider()
        settings = get_project_settings()
        crawler = Crawler(settings)
        crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
        crawler.signals.connect(self.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(self.engine_started, signals.engine_started)
        crawler.configure()
        crawler.crawl(spider)
        crawler.start()
        log.start(logstdout=True)
        print 'end initialize_scrapy'
    
    def item_scraped(self, *args):
        print args
    def engine_started(self, *args):
        print args

    @magic_arguments
    @argument(
        '-h', '--host', type=str, nargs='?', default='localhost',
        help='remote host'
    )
    @argument(
        '-p', '--port', type=int, nargs='?', default=13113,
        help='host port'
    )
    @line_magic
    def attach_scrapy(self, arg):
        args = parse_argstring(self.attach_scrapy, arg)
        host, port = args.host, args.port
        assert 1 <= port <= 65536

        global tn
        if tn is not None:
            tn.close()

        try:
            conn = self._get_connection(host, port)
        except socket.gaierror:
            raise ValueError("Wrong host: " + str(host))
        except socket.error:
            raise EOFError("Connection failure")

        tn = ServerSide(conn, self.shell)

        variables = tn.get_vars()
        if variables:
            self.shell.push(variables)
            print("Variables are loaded: {}".format(', '.join(variables)))
        return tn

    @magic_arguments
    @argument()
    @line_cell_magic
    def process_shell(self, args, source=None):
        if source is None:
            source = args
        else:
            source = args + '\n' + source
        res =  tn.execute(source)

        keys = tn.get_keys()
        for i in tn.keys - keys:
            self.shell.remove(i)
        tn.keys = keys
        self.shell.push(tn.get_vars())
        return res

    @line_magic
    def stop_scrapy(self, *args):
        tn.stop_scrapy()

    @line_magic
    def pause_scrapy(self, *args):
        tn.pause_scrapy()

    @line_magic
    def resume_scrapy(self, *args):
        tn.resume_scrapy()

    @line_magic
    def common_stats(self, *args):
        return tn.get_stats()

    @line_magic
    def spider_stats(self, *args):
        return tn.spider_stats

    @line_magic
    def print_source(self, args):
        obj = self.shell.ev(args)
        try:
            print(tn.get_source(obj))
        except (TypeError, IOError) as exc:
            print "Error:", exc

    @cell_magic
    def set_method(self, arg, text):
        arg = arg.strip()
        try:
            splitted = arg.split()
            obj, method_name = splitted
        except ValueError:
            splitted = arg.rsplit('.', 1)
            obj, method_name = splitted

        obj = self.shell.ev(obj)
        if not tn.is_remote(obj):
            raise ValueError("Object {} is a local, not remote".format(obj))
        tn.set_method(obj, method_name, text)

    @line_cell_magic
    def visualize_scrapy(self, *args):
        tn.visualize_scrapy()

def load_ipython_extension(ip):
    global _loaded
    if not _loaded:
        _loaded = True
        ip.register_magics(ScrapyNotebook)
    logger.debug("Loaded")


def unload_ipython_extension(ip):
    global tn
    if tn is not None:
        tn.close()
    tn = None
    logger.debug("Unload")