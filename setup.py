#!/usr/bin/env python

from setuptools import setup, find_packages

setup (
    name = "wallbox",
    version = "0.1",
    packages = find_packages ('src'),
    package_dir = {'':'src'},

    package_data = { 'wallbox': ['data/*.ui', 'data/images/*.gif', 'data/images/*.png'] },

    url = "http://github.com/yurenju/wallbox",
    author = "Yuren Ju",
    author_email = "yurenju@gmail.com",
    description = "Facebook notification for Linux",
    license = "GPL",

    entry_points = {
        'gui_scripts': [
            'wallbox = wallbox.wallbox:run_wallbox',
        ],
        'console_scripts': [
            'post_office = wallbox.post_office:main',
        ],

    },
)
