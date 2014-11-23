#!/bin/env python
# -*- encoding: utf-8 -*-


from scrapy.utils.trackref import print_live_refs
from scrapy.utils.engine import print_engine_status

from scrapy.crawler import Crawler
from scrapy import log
#from scrapy.utils.spider import DefaultSpider as spidercls
from scrapy.utils.project import get_project_settings

from ScrapyNotebook.utils import is_typeobj

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
    from scrapy.spider import Spider
    class DefaultSpider(Spider):
        name = 'default'

def get_spider(spider, url):
    if url is None:
        url = []
    elif not isinstance(url, (list, tuple)):
        url = [url]

    if spider is None:
        spider = DefaultSpider(start_urls=url)
    elif is_typeobj(spider):
        spider = spider(start_urls=url)
    return spider

def scrapy_embedding(spider=None, url=None):
    settings = get_project_settings()

    from scrapy.commands.shell import Command
    settings.setdict(Command.default_settings, priority='command')

    crawler = Crawler(settings)
    crawler.configure()
    if spider is not None:
        crawler.crawl(spider)
    crawler.start()
    #log.start(logstdout=False)
    return crawler

from scrapy.shell import Shell

class IPythonNotebookShell(Shell):

    def __init__(self, shell, *args, **kwargs):
        self.current_ipython_shell = shell
        super(IPythonNotebookShell, self).__init__(*args, **kwargs)

    def start(self, url=None, request=None, response=None, spider=None):
        if url:
            self.fetch(url, spider)
        elif request:
            self.fetch(request, spider)
        elif response:
            request = response.request
            self.populate_vars(response, request, spider)
        else:
            self.populate_vars()
        # ipython shell started
        # nothing to do

    def populate_vars(self,*args, **kwargs):
        super(IPythonNotebookShell, self).populate_vars(*args, **kwargs)
        self.current_ipython_shell.push(self.vars)
