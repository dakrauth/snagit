snarf
=====

Yet another scrapping tool.

``snarf`` allows you to scrape multiple pages or documents by either running
script files, or in the interactive REPL. For instance::

    $ snarf
    Type "help" for more information. Ctrl+c to exit
    > load http://httpbin.org/links/3/{} range='0-2'
    > print
    <html><head><title>Links</title></head><body>0 <a href='/links/3/1'>1</a> <a href='/links/3/2'>2</a> </body></html>
    <html><head><title>Links</title></head><body><a href='/links/3/0'>0</a> 1 <a href='/links/3/2'>2</a> </body></html>
    <html><head><title>Links</title></head><body><a href='/links/3/0'>0</a> <a href='/links/3/1'>1</a> 2 </body></html>
    > select a
    > print
    <a href="/links/3/1">1</a>
    <a href="/links/3/2">2</a>
    <a href="/links/3/0">0</a>
    <a href="/links/3/2">2</a>
    <a href="/links/3/0">0</a>
    <a href="/links/3/1">1</a>
    > unwrap_attr a href
    > print
    /links/3/1
    /links/3/2
    /links/3/0
    /links/3/2
    /links/3/0
    /links/3/1
    > list
    LOAD 'http://httpbin.org/links/3/{}' range='0-2'
    PRINT
    SELECT 'a'
    PRINT
    UNWRAP_ATTR 'a' 'href'
    PRINT


Features
--------

* Process data as either a text block, lines of text, or HTML (using BeautifulSoup)
* Built-in scripting language
* REPL for command line interaction

Requirements
------------

* Python 3.4+
* ``bs4`` (BeautifulSoup 4.x)
* ``requests``
* ``strutil``
* ``cachely``

For testing:

* ``pytest``
* ``pytest-cov``


Development and Testing
-----------------------

Assumptions: you have ``pip`` and ``virtualenv`` installed.

::

    $ virtualenv snarf
    $ source bin/activate
    $ git clone https://github.com/dakrauth/snarf.git
    $ cd snarf
    $ inv develop
    $ inv test
    $ inv cov
