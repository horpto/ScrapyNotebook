# -*- coding: utf-8 -*-

from ScrapyNotebook.utils import escape_html
from IPython.display import HTML

from scrapy_utils import get_selectors

class Frame(object):
    """
    Class to embed an html in cell of an IPython notebook
    """

    iframe = u"""
        <iframe
            src="{src}"
            width="{width}"
            srcdoc="{content}"
            height="{height}"
            frameborder="0"
            allowfullscreen
        ></iframe>
        """

    def __init__(self, content, src=u'', width=u"100%", height=u"100%"):
        self.src = src
        self.content = content
        self.width = width
        self.height = height

    def _repr_html_(self):
        # TODO: unicode
        content = escape_html(self.content)
        return self.iframe.format(src=self.src,
                                  content=content,
                                  width=self.width,
                                  height=self.height,
                                  )

def display_xpath(selectors_or_response, xpath=None, height=u"400"):
    """display list of elements selecting by xpath or list of selectors
    
    example:
        display_xpath(response, "body/*")
        
        selectors = response.xpath("div[@class="quotes"]")
        display_xpath(selectors)
    """
    selectors = get_selectors(selectors_or_response, xpath)
    frames = (Frame(selector.extract(), height=u"400")._repr_html_()
                  for selector in selectors)
    return HTML(u'<br/>'.join(frames))
