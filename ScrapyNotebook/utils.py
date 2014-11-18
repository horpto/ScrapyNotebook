#!/bin/env python
# -*- encoding: utf-8 -*-
import sys

from rpyc.core.stream import SocketStream
from scrapy.utils.trackref import print_live_refs
from scrapy.utils.engine import print_engine_status

from scrapy.crawler import Crawler
from scrapy import log
#from scrapy.utils.spider import DefaultSpider as spidercls
from scrapy.utils.project import get_project_settings


try:
    import guppy
    hpy = guppy.hpy()
except ImportError:
    hpy = None

import logging
logger = logging.getLogger()

SRC_LABEL_ATTR = '_rpyc_source_code'

# signal to update rpyc variables
# args: rpyc_vars
update_rpyc_vars = object()

def get_vars(crawler):
    rpyc_vars = {
        'engine': crawler.engine,
        'spider': crawler.engine.spider,
        'slot': crawler.engine.slot,
        'crawler': crawler,
        'extensions': crawler.extensions,
        'stats': crawler.stats,
        'spiders': crawler.spiders,
        'settings': crawler.settings,
        'est': lambda: print_engine_status(crawler.engine),
        'prefs': print_live_refs,
        'hpy': hpy,
    }
    crawler.signals.send_catch_log(update_rpyc_vars, rpyc_vars=rpyc_vars)
    return rpyc_vars

def create_function(src):
    env, code = {}, compile(src, '<input>', 'exec')
    eval(code, env) # DANGEROUS, not safety
    env.pop('__builtins__')
    keys = env.keys()
    if len(keys) != 1:
        raise ValueError("Should be only one function, but there is %s "
                            % keys)
    return env[keys[0]]

def mark_source_method(obj, method_name, src):
    if not isinstance(obj, type):
        obj = type(obj)
    func = create_function(src)
    setattr(func, SRC_LABEL_ATTR, src)


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

def print_err(arg):
    print >> sys.stderr, arg

try:
    from scrapy.utils import DefaultSpider
except:
    from scrapy.spider import BaseSpider
    class DefaultSpider(BaseSpider):
        name = 'default'

def scrapy_embedding(spidercls=None, url=None):
    spidercls = DefaultSpider if spidercls is None else spidercls
    spider = spidercls()
    spider.start_urls = [url]
    settings = get_project_settings()

    crawler = Crawler(settings)
    crawler.configure()
    crawler.crawl(spider)
    crawler.start()
    log.start(logstdout=False)
    return crawler

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
