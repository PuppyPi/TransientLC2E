#!/usr/bin/env python2

# Note that this requires a file named xyz.agent[s] to contain an agent named exactly, case-sensitively, "xyz" (we don't look inside the actual PRAY file, sorries :P )
# (or multiple, but that's the one we will test for!)

# Todo: allow overriding this on the command line :>''


import shutil;
from transientlc2e import *;

Tryagent_Default_Instance_Dir = "tryagent";
Tryagent_Default_Datapack_Dir = "tryagent";

TryagentCaosDebug = True;



def tryagentMain(args):
	def printHelp():
		print("usage: "+os.path.basename(sys.argv[0])+" [-v] [-m] [--rwdir=<dir>] [--rodir=[<dir>]] <agentfile>");
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
	
	
	
	
	
	# -m for manual injection! :D
	if ("-m" in args):
		doInjectionAutomatically = False;
		args.remove("-m");
	else:
		doInjectionAutomatically = True;   # 'manual' not 'not-automatic' so the default's automatic ;>
	
	
	# --rwdir= for reading AND writing, aka instance directory, aka primary dirs :>
	try:
		a = removeP(lambda arg: arg.startswith("--rwdir="), args);
	except KeyError:
		rwdir = Default;
	else:
		rwdir = a[len("--rwdir="):];
	
	if (rwdir == Default):
		if (Tryagent_Default_Instance_Dir == None): raise Exception();  #can't be none! it's the primary directories! D:
		rwdir = Tryagent_Default_Instance_Dir;
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
		rodir = Tryagent_Default_Datapack_Dir;   # *can* be None ;>
	elif (rodir == ""):
		rodir = None;
	if (rodir != None and not "/" in rodir):
		rodir = os.path.join(Transient_LC2E_RODataPacks_SuperDirectory, rodir);
	
	
	
	# --creator= for other tools using this!
	try:
		creator = removeP(lambda arg: arg.startswith("--creator="), args);
	except KeyError:
		creator = "TryAgent"
	
	
	
	# Rest of args :3
	if (len(args) == 1):
		agentFile = args[0];
	else:
		doPrintHelp();
		return 1;
	
	
	
	
	
	
	
#	try:
	return copyWorldStartLC2ELoadWorldInjectAgentWaitForUserAndTerminate(agentFile, config, creator, rwdir=rwdir, rodir=rodir, verbose=verbose, doInjectionAutomatically=doInjectionAutomatically, out=lambda msg: sys.stdout.write(msg+"\n"));
#		
#	except TryAgentException, exc:
#		# Super-nicely structured exception! :D!
#		
#		if (isinstance(exc, CaosErrorTryAgentException)):
#			todo..

#








class TryAgentException(Exception):
	pass;


class CaosErrorTryAgentException(TryAgentException):
	"Our caos had some kind of caos error :<    The script we tried in 'caoscode'; Resulting message output in 'returnMessage'    ._."
	caoscode = None;
	returnMessage = None;
	funky = True;  #..XD
	def __init__(self, caoscode, returnMessage): self.caoscode = caoscode; self.returnMessage = returnMessage;


class ChunkNotFoundTryAgentException(TryAgentException):
	pass;


class DependencyCountTagNotFoundTryAgentException(TryAgentException):
	"Note: this could actually technically falsely trigger, but I thinks it's unlikely XD, and the actual injection would have failed anyway :P"


class ScriptNotFoundTryAgentException(TryAgentException):
	"The attribute 'scriptName' gives the name of the offending script, as per the caos spec :>"
	scriptName = None;
	def __init__(self, scriptName): self.scriptName = scriptName;

class InjectionFailedTryAgentException(TryAgentException):
	"The attribute 'scriptName' gives the name of the offending script, as per the caos spec :>"
	scriptName = None;
	def __init__(self, scriptName): self.scriptName = scriptName;

class UnknownPrayInjtResultTryAgentException(TryAgentException):
	"An unknown return code or incorrect report var type from PRAY INJT! o,0!    (See also OfUnknownPrayInjtReportVarType)"
	returnCode = None;
	reportVar = None;
	funky = True;
	def __init__(self, returnCode, reportVar): self.returnCode = returnCode; self.reportVar = reportVar;

class OfUnknownPrayInjtReportVarType(object):
	"""
	The reportVar attribute in UnknownPrayInjtResultTryAgentException is set to one of these if PRAY INJT didn't make it either an integer or a string! ;;
	The 'typeCode' attribute of this is set to the caos TYPE command return value :>
	"""
	
	typeCode = None;
	def __init__(self, typeCode): self.typeCode = typeCode;


class DEPSAgentTypeNotFoundTryAgentException(TryAgentException):
	"PRAY INJT's built-in PRAY DEPS returned -1, but shouldn't the earlier PRAY TEST check have determined this, leading to a ChunkNotFoundTryAgentException???  (it also it want to throw caos errors too, right?!)  o,0!"
	funky = True;

class DEPSDependencyCountTagNotFoundTryAgentException(TryAgentException):
	"PRAY INJT's built-in PRAY DEPS returned -2, but shouldn't the earlier PRAY AGTI check have determined this, leading to a DependencyCountTagNotFoundTryAgentException???  o,0"
	funky = True;

class DependencyStringMissingTryAgentException(TryAgentException):
	"PRAY INJT's built-in PRAY DEPS returned 'dependency string missing' as per the spec :>"
	dependencyNumber = None;
	dependency = None;
	dependencyCategoryId = None;
	def __init__(self, dependencyNumber): self.dependencyNumber = dependencyNumber;

class DependencyTypeMissingTryAgentException(TryAgentException):
	"PRAY INJT's built-in PRAY DEPS returned 'dependency type missing' as per the spec :>"
	dependencyNumber = None;
	dependency = None;
	dependencyCategoryId = None;
	def __init__(self, dependencyNumber): self.dependencyNumber = dependencyNumber;

class DependencyCategoryIdInvalidTryAgentException(TryAgentException):
	"PRAY INJT's built-in PRAY DEPS returned 'dependency's category id is invalid' as per the spec :>"
	dependencyNumber = None;
	dependency = None;
	dependencyCategoryId = None;
	def __init__(self, dependencyNumber): self.dependencyNumber = dependencyNumber;

class DependencyFailedTryAgentException(TryAgentException):
	"PRAY INJT's built-in PRAY DEPS returned 'dependency failed' as per the spec :>"
	dependencyNumber = None;
	dependency = None;
	dependencyCategoryId = None;
	def __init__(self, dependencyNumber): self.dependencyNumber = dependencyNumber;




def copyWorldStartLC2ELoadWorldInjectAgentWaitForUserAndTerminate(agentFile, config, creator, agentName=None, rwdir=Default, rodir=Default, worldTemplate=None, verbose=False, doInjectionAutomatically=True, out=lambda msg: None):
	
	if (rwdir == Default):
		rwdir = os.path.join(config.rwDataInstancesSuperDirectory, Tryagent_Default_Instance_Dir)
	
	if (rodir == Default):
		rodir = os.path.join(config.roDataPacks_SuperDirectory, Tryagent_Default_Datapack_Dir) if Tryagent_Default_Datapack_Dir != None else None
	
	agentFile = os.path.abspath(agentFile);
	rwdir = os.path.abspath(rwdir);
	rodir = os.path.abspath(rodir) if rodir != None else None;
	
	if (agentName == None):
		agentName = os.path.splitext(os.path.basename(agentFile))[0];
	
	if (worldTemplate == None):
		d = os.path.join(rwdir, "Tryagent Template World Directory");   #won't conflict with anything else since we use CreaturesFilesystem default directory names and don't let the user override them >>''
		
		if (not os.path.isdir(d)):
			out("There needs to be a world-containing directory named "+repr(d)+" so we can delete the stale world and copy a fresh one each time (for happy debugging!) :>");
			return 16;
		
		c = os.listdir(d);
		
		if (len(c) != 1):
			out("There needs to be exactly one world inside "+repr(d)+" ;_;");
			out("That way we can know what the name of the world is for loading it! ;;");
			return 17;
		
		worldTemplate = os.path.join(d, c[0]);
	
	
	
	cfs = CreaturesFilesystem(rwdir);
	
	worldName = os.path.basename(worldTemplate);
	worldInstance = os.path.join(cfs.Worlds_Directory, worldName);
	
	# Ewww, get rid of the old stale one ><
	if (os.path.lexists(worldInstance)):
		shutil.rmtree(worldInstance);
	
	
	activeAgentFile = os.path.join(cfs.Resource_Files_Directory, os.path.basename(agentFile));
	
	
	def runcaos(theCaoscode):
		if (TryagentCaosDebug): out("====\n"+theCaoscode+"\n====\n-->\n====");  #por la debug >>  :>
		r = session.runcaos(theCaoscode);
		if (TryagentCaosDebug): out(r+"====\n\n\n\n");  #por la debug >>  :>
		return r;
	
	
	try:
		# Copy a fresh instance! :D
		shutil.copytree(worldTemplate, worldInstance);
		
		# Link in the agent file! :D
		os.symlink(os.path.abspath(agentFile), activeAgentFile);
		
		
		# Let's do this! \o/ :D
		session = TransientLC2ESession(config.roEngineTemplateDataDirectory);
		session.verbose = verbose;
		session.loadDefaultsFromConfig(config)
		session.loadCreaturesFilesystemIntoMachineConfigAsThePrimaryReadwriteFilesystem(cfs);
		if (rodir != None): session.loadCreaturesFilesystemIntoMachineConfigAsTheAuxiliaryReadonlyFilesystem(CreaturesFilesystem(rodir));
		configureTransientLC2ESessionForStandardDockingStation(session);
		session.start(creator, True);
		session.waitForEngineToBecomeCaosable();  #Will throw a TransientLC2ESessionStateException if the engine crashes or something instead of becoming caosable X'D
		
		
		caoscode = "load "+toCAOSString(worldName);
		
		r = runcaos(caoscode);
		
		if (r != ""):
			raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
		
		session.waitForEngineToBecomeCaosable();
		
		
		
		if (doInjectionAutomatically):
			caoscode = """
				sets va99 """+toCAOSString(agentName)+"""
				
				setv va00 pray test va99
				doif va00 <= 0
					outs "chunk not found"
				else
					
					setv va01 pray agti va99 "Dependency Count" -99999
					doif va01 = -99999
						outs "depedency count tag not found"
					
					else
						seta va03 pntr
						setv va02 pray injt va99 1 va03
						
						doif va02 <> 0
							outv va01
							outs " "
							outv va02
							outs " "
							
							doif type va03 = 0
								outs "I"
								outs " "
								outv va03
							elif type va03 = 2
								outs "S"
								outs " "
								outs va03
							elif type va03 = 4
								outs "X "
							else
								outs "? "
								outv type va03
							endi
						endi
					endi
				endi
			""";
			
			r = runcaos(caoscode);
			
			
			if (r == ""):
				# Success! :D
				pass;
			elif (r == "chunk not found"):
				raise ChunkNotFoundTryAgentException();
			elif (r == "depedency count tag not found"):
				raise DependencyCountTagNotFoundTryAgentException();
			else:
				# PRAY INJT error! ;_;
				
				if (not r[0] in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]):
					raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
				
				p = r.split(" ", 3);  #3 spaces normally, 2 spaces for "X" report vars :>
				
				if (len(p) < 3):
					raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
				
				try:
					dependencyCount = int(p[0]);
					prayInjtReturnCode = int(p[1]);
				except ValueError:
					raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
				
				typeCode = p[2];
				
				if (typeCode == "I"):
					try:
						reportVar = int(p[3]);
					except ValueError:
						raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
				elif (typeCode == "S"):
					reportVar = p[3];
				elif (typeCode == "X"):
					reportVar = None;
				elif (typeCode == "?"):
					try:
						actualTypeCode = int(p[3]);
					except ValueError:
						raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
					
					reportVar = OfUnknownPrayInjtReportVarType(actualTypeCode);
				else:
					raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
				
				
				
				
				# Interpret the PRAY INJT return code as per the CAOS docs! :D
				
				# Note that code 0 is handled by the caos above ;>
				if (prayInjtReturnCode == -1):
					# Script not found! D:
					if (not isinstance(reportVar, basestring)):
						raise UnknownPrayInjtResultTryAgentException(prayInjtReturnCode, reportVar);
					raise ScriptNotFoundTryAgentException(reportVar);
				
				elif (prayInjtReturnCode == -2):
					# Injection failed! D:
					if (not isinstance(reportVar, basestring)):
						raise UnknownPrayInjtResultTryAgentException(prayInjtReturnCode, reportVar);
					raise InjectionFailedTryAgentException(reportVar);
				
				elif (prayInjtReturnCode == -3):
					# Dependency error! ]:
					if (not isinstance(reportVar, int)):
						raise UnknownPrayInjtResultTryAgentException(prayInjtReturnCode, reportVar);
					
					# Interpret the PRAY DEPS return code as per the CAOS docs! :D
					prayDepsReturnCode = reportVar;
					
					if (prayDepsReturnCode == 0):  #..success??? o,0
						raise UnknownPrayInjtResultTryAgentException(prayInjtReturnCode, reportVar);
					elif (prayDepsReturnCode == -1):
						raise DEPSAgentTypeNotFoundTryAgentException();
					elif (prayDepsReturnCode == -2):
						raise DEPSDependencyCountTagNotFoundTryAgentException();
					else:
						
						# Note: I don't know the sign of the decoding! ;_;   Like, does -3 mean first-dependency is string-missing, or last-dependency is string-missing? ;-;
						
						if (prayDepsReturnCode < 0):
							c = -prayDepsReturnCode;
							c -= 1;  #minus 2 to offset it from the two special values, and + 1 because dependencies use 1-based indexes!
							if (c <= dependencyCount):
								error = DependencyStringMissingTryAgentException(c);
							c -= dependencyCount;
							if (c <= dependencyCount):
								error = DependencyTypeMissingTryAgentException(c);
							#otherwise it's out of bounds of the spec TT
							raise UnknownPrayInjtResultTryAgentException(prayInjtReturnCode, reportVar);
						else:
							#minus 1 to offset it from the one special value (0=success), and + 1 because dependencies use 1-based indexes!   ..so nothing! XD
							if (c <= dependencyCount):
								error = DependencyFailedTryAgentException(c);
							c -= dependencyCount;
							c += 1;  #1-based indexes!
							if (c <= dependencyCount):
								error = DependencyCategoryIdInvalidTryAgentException(c);
							#otherwise it's out of bounds of the spec TT
							raise UnknownPrayInjtResultTryAgentException(prayInjtReturnCode, reportVar);
						
						
						# Get the dependency resource name and category id through caos while we has the engine! :D
						
						
						dependencyNumber = error.dependencyNumber;
						
						caoscode = """
							sets va99 """+toCAOSString(agentName)+"""
							
							outv pray agti va99 """+toCAOSString("Dependency Category "+repr(dependencyNumber))+""" -99999
							outs " "
							outs pray agts va99 """+toCAOSString("Dependency "+repr(dependencyNumber))+""" "roirumoeircuamwelricalmewrcioamwoercaiwucrlmowimireallydon'tthinkanyoneisgoingtomaketheactualdependencybethissowecanassumeit'snotthereifweseethisXD"
						""";
						
						r = runcaos(caoscode);
						
						
						
						p = r.split(" ", 1);
						
						if (len(p) != 2):
							raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
						
						catPart, actualDependency = p;
						
						try:
							categoryId = int(catPart);
						except ValueError:
							raise CaosErrorTryAgentException(caoscode, r);   # Invalid format, it must be a caos syntax/runtime error message!
						
						# Stuff the extra useful things in there! ^w^
						error.dependency = actualDependency;
						error.dependencyCategoryId = categoryId;
						
						# Nowwww raise it! :D
						raise error;
				
				else:
					# ..wait what? xD'?
					raise UnknownPrayInjtResultTryAgentException(prayInjtReturnCode, reportVar);
		
		
		
		# If it's successful, the user's just supposed to quit or save-and-quit (which doesn't matter since the world is wiped and reset by us automatically! ;D )
		# once they're done testing out the agent! ^w^
		
		
	finally:
		try:
			session.waitForEngineToTerminate();
			
			session.cleanUp();
		except:
			pass;
		
		
		try:
			if (os.path.lexists(activeAgentFile)):
				os.unlink(activeAgentFile);
		except:
			pass;
		
		try:
			# Get rid of the now-stale one to be nice ^^
			if (os.path.lexists(worldInstance)):
				shutil.rmtree(worldInstance);
		except:
			pass;
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
	sys.exit(tryagentMain(sys.argv[1:]));
