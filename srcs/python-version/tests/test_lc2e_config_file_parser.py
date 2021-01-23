#!/usr/bin/env python2

import sys, os;

TopPythonDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TopDir = os.path.dirname(os.path.dirname(TopPythonDir))

sys.path.append(os.path.join(TopPythonDir, "main"))

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
	
	defaultTestDataDir = os.path.join(TopDir, "test-data");
	
	if (os.path.isdir(defaultTestDataDir)):
		args = map(lambda n: os.path.join(defaultTestDataDir, n), os.listdir(defaultTestDataDir));
	else:
		print("Couldn't find the test-data dir! D:")
		sys.exit(8)

for targetFile in args:
	print("Testing on "+repr(os.path.basename(targetFile))+" ... (cross your hooves!)  :>!");
	source = readallText(targetFile);
	
	try:
		runtest(source);
	except AssertionError:
		sys.stderr.write("Failed on file "+repr(targetFile)+"  D:!\n");
		raise;

print("All tests passed! :D!!");
