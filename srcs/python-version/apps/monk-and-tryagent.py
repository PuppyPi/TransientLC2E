#!/usr/bin/env python2

# Note that like tryagent this requires the agent name match up to the filename
# but ALSO the .cos file name match up to both the agent name and the filename!
# Which is how we tell what .agent[s] file to use!

# Todo: allow overriding this on the command line :>''


import sys;
import os, subprocess;


def monkAndTryAgentMain(args):
	if (len(args) >= 1):
		sourceFile = args[0];
		tryagentExtraArgs = args[1:];
	else:
		print("usage: "+os.path.basename(sys.argv[0])+" <cos-or-txt-file>");
		print("");
		print(":>");
	
	
	possiblePrayFiles = map(lambda s: os.path.splitext(sourceFile)[0]+s, [".agent", ".agents"]);
	
	
	
	# OKAY LET'S DO THIS! :D!!
	
	# IT'S MONKAY TIMEEEE!! :>
	print("MONKIFYING!! :D!");
	rc = execute("monk", sourceFile);
	
	if (rc != 0):
		print("Monk failed!? T_T");
		print("(exit status: "+repr(rc));
		return rc;
	
	
	# Now where'd that agents file get off to >,>
	print("");
	
	prayFile = None;
	for possiblePrayFile in possiblePrayFiles:
		if (os.path.isfile(possiblePrayFile)):
			if (prayFile != None):
				print("Muuuuuultiple of the possible pray files!?  How does we know which one to choose?  ;_;");
				return 32;
			
			prayFile = possiblePrayFile;
	
	if (prayFile == None):
		print("No pray file produced! D:");
		print("We expecteded one of: "+repr(possiblePrayFiles));
		print("But none were found ;_;");
		return 33;
	
	print("PRAY Agent file found at: "+prayFile+"    ^w^");
	print("");
	print("");
	
	
	
	# NOW IT'S TRYING-AGENTS TIMEEEE! :D
	print("TRYING AGENT!! :D");
	return execute("tryagent", prayFile, *tryagentExtraArgs);   #return its exit status directly as ours, since success here makes whole-thing-successful, and error here makes whole-thing-errored!  ^w^..'
#















# Utils! :D
def execute(command, *args):
	p = subprocess.Popen([command] + list(args));
	return p.wait();
#




# Necessary hook-thing in python codes to make it both an importable library module, *and* an executable program in its own right! :D    (like C and Java come with by default :P   which has good things and bad things :> )
if (__name__ == "__main__"):
	sys.exit(monkAndTryAgentMain(sys.argv[1:]));
