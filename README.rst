snarf
=====

Yet another scrapping tool.

Features
--------

* Process data as either a text block, lines of text, or HTML (using BeautifulSoup)
* Built-in scripting language
* Option for caching downloaded resources
* REPL for command line interaction

Requirements
------------

* Python 2.7
* ``bs4`` (BeautifulSoup 4.x)
* ``requests``

For testing:

* ``pytest``
* ``pytest-cov``


Testing
-------

Assumptions: you have ``pip`` and ``virtualenv`` installed.

::

    $ virtualenv snarf
    $ source bin/activate
    $ git clone https://github.com/dakrauth/snarf.git
    $ cd snarf
    $ make init
    $ make test      # -- OR --
    $ make unittest  # -- OR --
    $ make coverage

