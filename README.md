# snagit

[![Tests](https://github.com/dakrauth/snagit/actions/workflows/test.yml/badge.svg)](https://github.com/dakrauth/snagit)


Yet another scrapping tool.

## Installation

  ```console
  $ pip install snagit
  ```

Or, to use lxml as your primary parser:

  ```console
  $ pip install snagit[lxml]
  ```

``snagit`` allows you to scrape multiple pages or documents by either running
script files, or by using an interactive REPL. For instance:

  ```console
  $ snagit
  Type "help" for more information. Ctrl+c to exit
  > load http://httpbin.org/links/3/{} range=0-2
  > print
  <html><head><title>Links</title></head><body>0 <a href='/links/3/1'>1</a> <a href='/links/3/2'>2</a> </body></html>
  <html><head><title>Links</title></head><body><a href='/links/3/0'>0</a> 1 <a href='/links/3/2'>2</a> </body></html>
  <html><head><title>Links</title></head><body><a href='/links/3/0'>0</a> <a href='/links/3/1'>1</a> 2 </body></html>
  > strain a
  > print
  <a href="/links/3/1">1</a>
  <a href="/links/3/2">2</a>
  <a href="/links/3/0">0</a>
  <a href="/links/3/2">2</a>
  <a href="/links/3/0">0</a>
  <a href="/links/3/1">1</a>
  > unwrap a attr=href
  > print
  /links/3/1
  /links/3/2
  /links/3/0
  /links/3/2
  /links/3/0
  /links/3/1
  > list
  load http://httpbin.org/links/3/{} range=0-2
  print
  strain a
  print
  unwrap a attr=href
  print
  ```

## Features

* Process data as either a text block, lines of text, or HTML (using BeautifulSoup)
* Built-in scripting language
* REPL for command line interaction

## Requirements

* Python 3.11+
* ``bs4`` (BeautifulSoup 4.13+)
* ``cachely`` 0.2+


## Development and Testing

Using the convenience script ``run``:

 ```console
  $ git clone https://github.com/dakrauth/snagit.git
  $ cd snagit
  $ ./run init
  $ ./run test

  python -m venv --prompt snagit .venv
  $ . .venv/bin/activate
  ```
