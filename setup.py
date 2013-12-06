#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2013 Ivan F. Villanueva B. <ivan@wikical.com>
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution.

# Based on TracTicketStatsPlugin by
# Copyright (c) 2008-2009 Prentice Wongvibulsin <me@prenticew.com>
# Copyright (c) 2010-2012 Ryan J Ollos <ryan.j.ollos@gmail.com>

from setuptools import find_packages, setup

setup(
    name='TracSimpleTicketStatsPlugin',
    version='0.2',
    author='Ivan F. Villanueva B.',
    author_email='ivan@wikical.com',
    maintainer='Ivan F. Villanueva B.',
    maintainer_email='ivan@wikical.com',
    license='BSD 3-Clause',
    url='https://github.com/wikical/TracSimpleTicketStatsPlugin',
    description='Visualize ticket statistics with flotcharts.org js library',
    packages=find_packages(exclude=['*.tests']),
    entry_points="""
        [trac.plugins]
        simpleticketstats.macro = simpleticketstats.macro
    """,
    install_requires=['Trac >= 0.11'],
    package_data={'simpleticketstats': ['templates/*.html', 'htdocs/js/*.js']},
)
