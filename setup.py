#!/usr/bin/env python
import os, sys
from setuptools import setup

if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    sys.exit(0)

with open('README.rst', 'r') as f:
    long_description = f.read()

# Dynamically calculate the version based on swingtime.VERSION.
version=__import__('snarf').get_version()

setup(
    name='snarf',
    url='https://github.com/dakrauth/snarf',
    author='David A Krauth',
    author_email='dakrauth@gmail.com',
    description='Simple tools for downloading, cleaning, extracting and parsing content',
    version=version,
    long_description=long_description,
    platforms=['any'],
    license='MIT License',
    classifiers=(
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ),
    packages=['snarf'],
    install_requires=['requests', 'beautifulsoup4', 'strutil'],
    entry_points = {
        'console_scripts': ['snarf = snarf.__main__:main']
    }
)