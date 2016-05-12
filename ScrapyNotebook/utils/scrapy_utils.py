#!/bin/env python
# -*- encoding: utf-8 -*-


from scrapy.utils.trackref import print_live_refs
from scrapy.utils.engine import print_engine_status

from scrapy.crawler import Crawler
#from scrapy import log
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
        return None

    if spider is None:
        spider = DefaultSpider()
    elif is_typeobj(spider):
        spider = spider()
    return spider

def scrapy_embedding(spider=None, url=None):
    settings = get_project_settings()

    from scrapy.commands.shell import Command
    settings.setdict(Command.default_settings, priority='command')

    crawler = Crawler(settings)
    crawler.configure()
    crawler.start()
    #log.start(logstdout=False)
    return crawler

from scrapy.shell import Shell
from scrapy.http import Request
from w3lib.url import any_to_uri

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

    def fetch(self, request_or_url, spider=None):
        if isinstance(request_or_url, Request):
            request = request_or_url
            url = request.url
        else:
            url = any_to_uri(request_or_url)
            request = Request(url, dont_filter=True)
            request.meta['handle_httpstatus_all'] = True

        # ToDo: Bad solution - not work.
        def callback(x):
            parent = self.current_ipython_shell.get_parent()
            self.current_ipython_shell.kernel._publish_status('busy', parent)
            response, spider = x
            self.populate_vars(response, request, spider)
            self.current_ipython_shell.kernel._publish_status('idle', parent)
        def errback(err):
            parent = self.current_ipython_shell.get_parent()
            self.current_ipython_shell.kernel._publish_status('busy', parent)
            err.printTraceback()
            self.current_ipython_shell.kernel._publish_status('idle', parent)

        d = self._schedule(request, spider)
        d.addCallback(callback)
        d.addErrback(errback)
