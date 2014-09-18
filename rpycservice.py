"""Scrapy RPyC Extension"""

from twisted.internet import protocol

from scrapy.exceptions import NotConfigured
from scrapy import log, signals
from scrapy.utils.trackref import print_live_refs
from scrapy.utils.engine import print_engine_status
from scrapy.utils.reactor import listen_tcp


import pprint
import rpyc

try:
    import guppy
    hpy = guppy.hpy()
except ImportError:
    hpy = None


class RPyCProtocol(protocol.Protocol):
    def __init__(self, conn, service, channel, *args, **kwargs):
        self.conn = conn
        self.args = args
        self.kwargs = kwargs

    def connectionMade(self):
        print(self.transport)
        self.conn = self.conn(self.args, self.kwargs)

    def dataReceived(self, data):
        self.conn._dispatch(data)

    def connectionLost(self, reason):
        self.conn.close()


# signal to update rpyc variables
# args: rpyc_vars
update_rpyc_vars = object()

class RPyCService(protocol.ServerFactory):
    protocol = RPyCProtocol

    def __init__(self, crawler):
        if not crawler.settings.getbool('RPYCSERVICE_ENABLED'):
            raise NotConfigured
        self.crawler = crawler
        self.noisy = False
        self.portrange = [int(x) for x in crawler.settings.getlist('RPYCSERVICE_PORT')]
        self.host = crawler.settings['RPYCSERVICE_HOST']
        self.crawler.signals.connect(self.start_listening, signals.engine_started)
        self.crawler.signals.connect(self.stop_listening, signals.engine_stopped)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)
        
    def start_listening(self):
        self.port = listen_tcp(self.portrange, self.host, self)
        h = self.port.getHost()
        log.msg(format="RPyC service listening on %(host)s:%(port)d",
                level=log.DEBUG, host=h.host, port=h.port)
        self.crawler.signals.connect(self.item_scraped,
                signals.item_scraped)

    def stop_listening(self):
        self.port.stopListening()

    def protocol(self):
        rpyc_vars = self._get_vars()
        return RPyCProtocol(rpyc.Connection, rpyc_vars)

    def _get_vars(self):
        slots = self.crawler.engine.slots
        if len(slots) == 1:
            spider, slot = slots.items()[0]
        rpyc_vars = {
            'engine': self.crawler.engine,
            'spider': spider,
            'slot': slot,
            'crawler': self.crawler,
            'extensions': self.crawler.extensions,
            'stats': self.crawler.stats,
            'spiders': self.crawler.spiders,
            'settings': self.crawler.settings,
            'est': lambda: print_engine_status(self.crawler.engine),
            'p': pprint.pprint,
            'prefs': print_live_refs,
            'hpy': hpy,
            #'help': "This is Scrapy telnet console. For more info see: " \
            #    "http://doc.scrapy.org/en/latest/topics/telnetconsole.html",
        }
        self.crawler.signals.send_catch_log(update_rpyc_vars, rpyc_vars=rpyc_vars)
        return rpyc_vars

