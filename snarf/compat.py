from __future__ import unicode_literals
import sys

ver = sys.version_info[0]
is_py2 = ver == 2
is_py3 = ver == 3
is_windows = 'win32' in str(sys.platform).lower()
del ver

if is_py2:
    bytes = str
    str = unicode
