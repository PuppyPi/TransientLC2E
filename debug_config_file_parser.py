#!/usr/bin/env python

import sys;
from transientlc2e import *;

source = sys.stdin.read();

d = parseCreaturesConfig(source);

print repr(d);
