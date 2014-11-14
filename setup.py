#!/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from os.path import join, dirname
import ScrapyNotebook


setup(
    name='ScrapyNotebook',
    version=ScrapyNotebook.__version__,
    url='http://github.com/horpto/ScrapyNotebook',
    description='just extension for Scrapy and IPython',
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    packages=find_packages(),
    zip_safe=False,
    install_requires=[
        'scrapy',
        'ipython',
        'rpyc>=3.0'
    ],
    license='mit',
)
