# -*- coding: utf-8 -*-

from  ScrapyNotebook.utils import escape_html

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

    def __init__(self, src, content, width=u"100%", height=u"100%"):
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