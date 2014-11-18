#!/bin/env python
# -*- encoding: utf-8 -*-


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
