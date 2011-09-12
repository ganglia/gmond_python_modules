#!/usr/bin/python

import os
import sys
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


def allfiles(path):
    all_files = []
    for dirname, _, files in os.walk(path):
        all_files.extend( os.path.join(dirname, filename) for filename in files )
    return all_files


setup(
    name = "ganglia-openstack-monitor",
    version = "0.0.1a1",
    description = "Ganglia python plugin for Openstack Nova monitoring",
    long_description = read('README'),
    url = 'https://github.com/chemikadze/gmond_python_modules/tree/master/openstack_nova_stats',
    license = 'Apache 2',
    author = 'Nikolay Sokolov',
    author_email = 'nsokolov@griddynamics.com',
    data_files = [('/usr/local/share/openstack_nova_stats/graph.d', allfiles(os.path.join(os.path.dirname(__file__), 'graph.d'))),
                  ('/usr/local/share/doc/openstack_nova_stats', ['README']),
                  ('/etc/ganglia/conf.d', ['conf.d/compute-metrics.pyconf']),
                  ('/etc/ganglia/python_modules', allfiles(os.path.join(os.path.dirname(__file__), 'python_modules')))],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
