#!/bin/env python
# -*- encoding: utf-8 -*-

__version__ = '2.0'


# Wrapper for a module with extension
# Because %install_ext copies only file
# and extension directory consist on sys.path
# this file's name and extension's name should not be equal
from ScrapyNotebook.notebook_extension import (load_ipython_extension,
                                               unload_ipython_extension,)
