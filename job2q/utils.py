# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import os
import sys
from builtins import str
from collections import Iterable
from errno import EEXIST, ENOENT
from itertools import repeat

from job2q import messages
from job2q.exceptions import *

def makedirs(path):
    try: os.makedirs(path)
    except FileExistsError as e:
        if e.errno != EEXIST:
            raise

def remove(path):
    try: os.remove(path)
    except FileNotFoundError as e:
        if e.errno != ENOENT:
            raise

def rmdir(path):
    try: os.rmdir(path)
    except FileNotFoundError as e:
        if e.errno != ENOENT:
            raise

def hardlink(source, dest):
    try: os.link(source, dest)
    except FileExistsError as e:
        if e.errno == EEXIST:
            os.remove(dest)
            os.link(source, dest)
    except FileNotFoundError as e:
        if e.errno != ENOENT:
            raise

def expandall(path):
    return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))

def strjoin(*args, sep='', gen=repeat):
    def iterjoin(*args, sepgen):
        return next(sepgen).join(i if isinstance(i, str) else iterjoin(*i, sepgen=sepgen) if isinstance(i, Iterable) else str(i) for i in args if i)
    return iterjoin(*args, sepgen=gen(sep))

def wordjoin(*args):
    return strjoin(*args, sep=' ')

def linejoin(*args):
    return strjoin(strjoin(*args, sep='\n'), '\n')

def pathjoin(*args):
    return strjoin(*args, sep=os.sep+'.-', gen=iter)
    #return os.path.join(*['.'.join(str(j) for j in i) if type(i) is list else str(i) for i in args])

def p(string):
    return '({0})'.format(string)

def q(string):
    return '"{0}"'.format(string)

def qq(string):
    return '"\'{0}\'"'.format(string)

def natsort(text):
    return [ int(c) if c.isdigit() else c for c in re.split('(\d+)', text) ]

def loalnum(string): 
    return ''.join(c.lower() for c in string if c.isalnum())
