snarf
=====

Yet another scrapping tool.

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
