#!/usr/bin/env python

# PyCells: Automatic dataflow management for Python
# Copyright (C) 2006, Ryan Forsythe

import ez_setup
ez_setup.use_setuptools()
from setuptools import setup, find_packages

setup(name='PyCells',
      version='0.1b1',
      packages=find_packages(),
      extras_require = { 'Epydoc': ['epydoc>=2.1'], },
    
      description='Automatic dataflow management',
      author='Ryan Forsythe',
      author_email='ryan@pdxcb.net',
      url='http://pycells.pdxcb.net/',
      license="LGPL",
     )

