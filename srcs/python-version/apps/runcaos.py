#!/usr/bin/env python2

from transientlc2e import *;

Runcaos_Default_Instance_Dir = "skeleton";
Runcaos_Default_Datapack_Dir = None;


def runcaosMain(args):
	def printHelp():
		print("usage: "+os.path.basename(sys.argv[0])+" [-v] [--rwdir=<dir>] [--rodir=[<dir>]]  <caoscodes...>");
		print("or:    "+os.path.basename(sys.argv[0])+" [-v] [--rwdir=<dir>] [--rodir=[<dir>]]   <  <input>");
		print("");
		print(":>");
	
	
	# Printing help! :D
	if (len(args) == 0 or "-h" in args or "--help" in args):
		printHelp()
		return 0
	
	
	# -v for verbose! :D
	if ("-v" in args):
		verbose = True;
		args.remove("-v");
	else:
		verbose = False;
	
	
	
	try:
		config = loadDefaultConfig()
	except ConfigLoadingException, e:
		print("Error loading config!: "+e.message)
		return 8
	
	
	
	# --rwdir= for reading AND writing, aka instance directory, aka primary dirs :>
	try:
		a = removeP(lambda arg: arg.startswith("--rwdir="), args);
	except KeyError:
		rwdir = Default;
	else:
		rwdir = a[len("--rwdir="):];
	
	if (rwdir == Default):
		if (Runcaos_Default_Instance_Dir == None): raise Exception();  #can't be none! it's the primary directories! D:
		rwdir = Runcaos_Default_Instance_Dir;
	if (not "/" in rwdir):
		rwdir = os.path.join(config.rwDataInstancesSuperDirectory, rwdir);
	
	
	
	# --rodir= for reading ONLY, aka data-pack directory, aka auxiliary dirs :>
	try:
		a = removeP(lambda arg: arg.startswith("--rodir="), args);
	except KeyError:
		#absence, like above, means 'default' :>
		#use an empty string (ie, "--rodir=" ) to actually explicitly specify no-rodir ^_^
		rodir = Default;
	else:
		rodir = a[len("--rodir="):];
	
	if (rodir == Default):
		rodir = Runcaos_Default_Datapack_Dir;   # *can* be None ;>
	elif (rodir == ""):
		rodir = None;
	if (rodir != None and not "/" in rodir):
		rodir = os.path.join(Transient_LC2E_RODataPacks_SuperDirectory, rodir);
	
	
	
	# Rest of args :3
	if (len(args) == 0):
		caoscodes = [sys.stdin.read()];
	else:
		caoscodes = args;
	
	
	
	
	
	
	
	startLC2ERunCaosAndTerminate(caoscodes, config, rwdir, rodir, verbose=verbose, out=lambda msg: sys.stdout.write(msg+"\n"));
#





def startLC2ERunCaosAndTerminate(caoscodes, config, rwdir, rodir=None, verbose=False, out=lambda msg: None):
	session = TransientLC2ESession(config.roEngineTemplateDataDirectory);
	
	session.verbose = verbose;
	
	session.loadDefaultsFromConfig(config)
	
	session.loadCreaturesFilesystemIntoMachineConfigAsThePrimaryReadwriteFilesystem(CreaturesFilesystem(rwdir));
	if (rodir != None): session.loadCreaturesFilesystemIntoMachineConfigAsTheAuxiliaryReadonlyFilesystem(CreaturesFilesystem(rodir));
	
	# Apparently we have to set the default music even though we're running on a skeleton pack XD'
	configureTransientLC2ESessionForStandardDockingStation(session);
	
	session.start();
	
	session.waitForEngineToBecomeCaosable();
	
	for caoscode in caoscodes:
		# Not doing waitForEngineToBecomeCaosable between each one is a nice stress test to see if we don't have to wait! XD
		r = session.runcaos(caoscode);
		out(r);
	
	session.quitWithoutSaving();
	
	session.waitForEngineToTerminate();
	
	session.cleanUp();
#





# Utils! :D
def removeP(predicate, aList):
	i = findP(predicate, aList);
	if (i == None):
		raise KeyError();
	else:
		e = aList[i];
		del aList[i];
		return e;
#

def findP(predicate, aList):
	for i in xrange(len(aList)):
		if (predicate(aList[i])):
			return i;
	return None;
#




# Necessary hook-thing in python codes to make it both an importable library module, *and* an executable program in its own right! :D    (like C and Java come with by default :P   which has good things and bad things :> )
if (__name__ == "__main__"):
	sys.exit(runcaosMain(sys.argv[1:]));
