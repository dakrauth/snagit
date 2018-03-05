#!/usr/bin/env python
import os, sys
from setuptools import find_packages, setup


with open('README.rst', 'r') as f:
    long_description = f.read()

# Dynamically calculate the version.
version=__import__('snagit').get_version()


setup(
    name='snagit',
    url='https://github.com/dakrauth/snagit',
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
    packages=find_packages(),
    install_requires=['requests', 'beautifulsoup4', 'strutil'],
    entry_points = {
        'console_scripts': ['snagit = snagit.__main__:main']
    }
)
