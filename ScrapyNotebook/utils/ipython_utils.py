# -*- coding: utf-8 -*-

from ScrapyNotebook.utils import is_valid_url

def get_ipython_variables(shell):
    who_ls = shell.find_line_magic('who_ls')
    return {var: shell.ev(var) for var in who_ls()}

def get_url_from_ipython(url, shell):
    if not is_valid_url(url) and url is not None:
        url = shell.ev(url)
    return url

def get_value_in_context(obj, scrapy_side, shell):
    try:
        return scrapy_side.eval(obj)
    except:
        return shell.ev(obj)
