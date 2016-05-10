#!/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Fri Sep 26 13:54:42 2014

@author: Александр
"""
import rpyc

from ScrapyNotebook.utils import print_err
from ScrapyNotebook.utils.scrapy_utils import get_vars
from ScrapyNotebook.utils.sources import (mark_source_method, get_source)


class ScrapySide(object):
    builtins = set(('__builtin__', ))
    closed = False

    def __init__(self, shell, namespace):
        self.shell = shell
        self.namespace = namespace
        self.keys = self.get_keys #get_keys depends on namespace

        stats = self.namespace['stats']
        self.get_stats = stats.get_stats
        self.spider_stats = stats.spider_stats
        self.engine = self.namespace['engine']

    def __del__(self):
        self.close()

    def close(self):
        raise NotImplementedError('Not implemented method close')

    def stop_scrapy(self):
        self.engine.stop()

    def pause_scrapy(self):
        self.engine.pause()

    def resume_scrapy(self):
        self.engine.unpause()

    def visualize_scrapy(self):
        print_err('Not implemented yet')

    def push_variables(self, vars):
        for var, val in vars.iteritems():
            self.namespace[var] = val

    @property
    def get_keys(self):
        keys = set(self.namespace.keys()) - self.builtins
        return keys

    def get_source(self, obj):
        return get_source(obj)

class LocalScrapy(ScrapySide):

    def __init__(self, shell, crawler):
        self.crawler = crawler
        namespace = get_vars(crawler)

        super(LocalScrapy, self).__init__(shell, namespace)

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.crawler.stop()

    def eval(self, text):
        return eval(text, self.namespace)

    def execute(self, text):
        exec text in self.namespace

    def set_method(self, obj, method_name, src):
        func = mark_source_method(obj, method_name, src)
        setattr(obj, method_name, func)


class RemoteScrapy(ScrapySide):

    def __init__(self, shell, conn):
        namespace = conn.namespace
        super(RemoteScrapy, self).__init__(shell, namespace)
        self.conn = conn
        self.redir = rpyc.classic.redirected_stdio(self.conn)

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

    def eval(self, line):
        self.conn.eval(line)

    def execute(self, text):
        self.conn.execute(text)

        try:
            del self.conn.namespace['__builtins__']
        except KeyError:
            pass

    def push_variables(self, vars):
        for var, val in vars.iteritems():
            self.conn.root.namespace[var] = val

    def get_source(self, obj):
        return self.conn.root.get_source(obj)

    def set_method(self, obj, method_name, text):
        self.conn.root.set_source(obj, method_name, text)
