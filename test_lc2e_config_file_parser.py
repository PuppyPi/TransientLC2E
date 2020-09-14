#!/usr/bin/env python

import sys, os;
from transientlc2e import *;

args = sys.argv[1:];

def runtest(source):
	d = parseCreaturesConfig(source);
	
	redoneSource = serializeCreaturesConfig(d);
	
	reparsed = parseCreaturesConfig(redoneSource);
	
	if (reparsed != d):
		raise AssertionError("parsing, serializing, then reparsing should *always* yield the same results! D:   (source: "+repr(source)+")");
#


if (len(args) == 0):
	#source = sys.stdin.read();
	#runtest(source);
	
	defaultTestDataDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test config datas");
	
	if (os.path.isdir(defaultTestDataDir)):
		args = map(lambda n: os.path.join(defaultTestDataDir, n), os.listdir(defaultTestDataDir));

for targetFile in args:
	print("Testing on "+repr(os.path.basename(targetFile))+" ... (cross your hooves!)  :>!");
	source = readallText(targetFile);
	
	try:
		runtest(source);
	except AssertionError:
		sys.stderr.write("Failed on file "+repr(targetFile)+"  D:!\n");
		raise;

print("All tests passed! :D!!");
