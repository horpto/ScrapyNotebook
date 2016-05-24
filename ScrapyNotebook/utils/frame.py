# -*- coding: utf-8 -*-

from  ScrapyNotebook.utils import escape_html

class Frame(object):
    """
    Class to embed an html in cell of an IPython notebook
    """

    iframe = """
        <iframe
            src="{src}"
            width="{width}"
            srcdoc="{content}"
            height="{height}"
            frameborder="0"
            allowfullscreen
        ></iframe>
        """

    def __init__(self, src, content, width="100%", height="100%"):
        self.src = src
        self.content = content
        self.width = width
        self.height = height

    def _repr_html_(self):
        content = escape_html(self.content)
        return self.iframe.format(src=self.src,
                                  content=content,
                                  width=self.width,
                                  height=self.height,
                                  )