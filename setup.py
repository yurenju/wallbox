#!/usr/bin/env python

from setuptools import setup, find_packages
import ez_setup

ez_setup.use_setuptools ()

setup (
    name = "wallbox",
    version = "0.1",
    packages = find_packages ('src'),
    package_dir = {'':'src'},

    package_data = { 'wallbox': ['data/*.ui', 'data/images/*.gif'] },

    url = "http://github.com/yurenju/wallbox",
    author = "Yuren Ju",
    author_email = "yurenju@gmail.com",
    description = "Facebook notification for Linux",
    license = "GPL",
)
