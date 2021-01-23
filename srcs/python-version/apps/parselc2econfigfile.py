#!/usr/bin/env python2

import sys, os;
import json;
from transientlc2e import *;

args = sys.argv[1:];

if (len(args) == 0):
	source = sys.stdin.read();
	
	d = parseCreaturesConfig(source);
	
	print json.dumps(d, indent=1, sort_keys=True);
else:
	for targetFile in args:
		source = readallText(targetFile);
		
		d = parseCreaturesConfig(source);
		
		if (targetFile.endswith(".cfg")):
			destFile = targetFile[:-len(".cfg")] + ".json";
		else:
			destFile = targetFile + ".json";
		
		if (os.path.lexists(destFile)):
			sys.stderr.write("File exists: "+repr(destFile)+"  D:\n");
		else:
			jsoned = json.dumps(d, indent=1, sort_keys=True);
			
			writeallText(destFile, jsoned);
