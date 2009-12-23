#!/usr/bin/env python

from setuptools import setup, find_packages

setup (
    name = "wallbox",
    version = "0.1",
    packages = find_packages ('wallbox'),
    package_dir = {'': 'wallbox'},

    package_data = {
        '': ['data/*'],
    },

    author = "Yuren Ju",
    author_email = "yurenju@gmail.com",
    description = "Facebook notification for Linux",
    license = "GPL",
)
