#!/usr/bin/env python2

import sys, threading, weakref, atexit, random;
import time, errno, os, subprocess, socket;
import json;

from random import Random

Default = object();

UserDir = os.path.join(os.getenv("HOME"), ".tlc2e")



# Known transience sandbox failures!:
#	+ Main Directory / "port"
#	+ Main Directory / "caos.syntax"
#		But these seem not to cause much problem :>'
#	If it does, we can make TransientLC2E take over this like it does the home directory ^w^



class ConfigLoadingException(Exception):
	pass

class TransientLC2EConfiguration(object):
	transientSessionsSuperDirectory = None
	rwDataInstancesSuperDirectory = None
	roDataPacksSuperDirectory = None
	roEngineTemplateDataDirectory = None
	errorReportPackagesDirectory = None

def loadDefaultConfig():
	"Returns a TransientLC2EConfiguration on success, or throws a ConfigLoadingException with the message for the user on failure"
	
	ConfFile = os.path.join(UserDir, "config.json")
	DefaultContentDir = os.path.join(UserDir, "content")
	
	if (os.path.isfile(ConfFile)):
		h = open(ConfFile, "r")
		try:
			Config = json.load(h)
		finally:
			h.close()
	else:
		Config = {}
	
	def resolveIfRelative(p):
		if (os.path.isabs(p)):
			return p
		else:
			return os.path.join(DefaultContentDir, p)
	
	def getpath(k):
		v = Config.get(k)
		return resolveIfRelative(v if v != None else k)
	
	config = TransientLC2EConfiguration()
	config.transientSessionsSuperDirectory = getpath("running-transient-sessions");
	config.rwDataInstancesSuperDirectory = getpath("rw-instances");
	config.roDataPacksSuperDirectory = getpath("ro-datapacks");
	config.roEngineTemplateDataDirectory = getpath("ro-engine");
	config.errorReportPackagesDirectory = getpath("error-reports");
	return config
#










def configureTransientLC2ESessionForStandardDockingStation(sessionObject):
	"Note: we're horribly game neutral, so this is a separate convenience function, and you has to explicitly call it by default :P   (unless the skeleton config files are used and include the stuff! :> )"
	sessionObject.setPrimaryGameName("Docking Station");
	sessionObject.setAuxiliaryGameName("Creatures 3");
	sessionObject.getUserConfig()["Default Background"] = "ds_splash";
	sessionObject.getUserConfig()["Default Munge"] = "ds_music.mng";
#


class TransientLC2ESession(object):
	# Intended-to-be class constants :>   (all the same in python XD')
	State_Unstarted = 0;
	State_Running = 1;
	State_Terminated = 2;
	State_CleanedUp = 3;
	State_CleanedUpNeverProperlyStarted = 4;
	
	@classmethod
	def fmtstate(theClass, state): return ["unstarted", "running", "terminated", "cleaned-up", "cleaned-up-failed"][state];
	
	
	
	# Intended-to-be instance vars :>   (all the same in python XD')
	state = State_Unstarted;
	
	capturedLog = "";
	
	"session.log: Set here and always used so you can make it whatever you want ^w^  (eg, replace the function with something that captures all the logging messages and stores them in memory!, writes to a file!, displays in a gui!, etc.c.c.c. :D     (this applies to all console/loggings things do ;D )"
	log = None;
	
	
	
	# {Set beforehand
	# Config needed before starting! :D
	# note: don't set these after it's started / in State_Running; they won't have an effect x>'
	roEngineTemplateDir = None;  #The readonly directory holding the engine stuff for us to link to!  (Type: string that is a pathname ^_^)
	rwActiveSessionEngineDir = None;  #The writeable directory for us to link the engine stuff *into*!  (autonamed and autocreated if None ^w^ )    (Type: string that is a pathname ^_^)
	rwActiveSessionHomeDir = None;  #The writeable directory the engine does things in thinking it's our home dir (aka "~")   ..it doesn't have to be our actual home dir ;33   (esp. important if you want to, you know, run more than a single individual instance of the engine throughout the ENTIRE COMPUTER SYSTEM (for that user) at a time! XD''' )
	machineConfig = None;   #a dict representing contents of maching.cfg  ^_^
	userConfig = None;      #a dict representing contents of user.cfg  ^_^
	serverConfig = None;    #a dict representing contents of server.cfg  ^_^
	passwordConfig = None;  #a dict representing contents of password.cfg  ^_^
	languageConfig = None;  #a dict representing contents of language.cfg  ^_^
	# Note: if a config dict is None, then that file just won't be generated :>   (eg, for optional ones like language.cfg or password.cfg ^_^ )
	
	libfilebasenamesInSameDirAsEngine = None;  #Note that mutable objects as variable-defaults in python class files are shared amongst ALL INSTANCES FOR ALL OF TIME 0_0   (but we can set them in __init__ because literals are copied!  ^^'' )
	
	dataToFeedToStdin = None;
	captureStdout = True;
	captureStderr = True;
	
	errorReportPackagesDirectory = None;
	# Set beforehand}
	
	
	
	# Valid only while in running state! :>
	process = None;  #the python "subprocess" module's process object of the engine! :D
	
	
	# Valid only while in >= Terminated state!
	# The postXyzConfig's are parsed dicts, the postXyzConfigRaw's are the serialized raw form (str's!)  :>!
	postMachineConfig = None; postMachineConfigRaw = None; #postXyzConfig's are re-read after the engine terminates! ^w^
	postUserConfig = None; postUserConfigRaw = None;
	postServerConfig = None; postServerConfigRaw = None;
	postPasswordConfig = None; postPasswordConfigRaw = None;
	postLanguageConfig = None; postLanguageConfigRaw = None;
	
	postLogfile = None;  #unmodified contents of "creatures_engine_logfile.txt" after the engine terminates ^_^
	postUnexpectedFileBasenames = None;  # a python 'set' object of all the files (basenames) which were in the active engine session directory after it terminated, but that we *weren't* expecting to be there! 0_0     (hey, I don't know everything about lc2e!  (#understatement) XD! )          The actual files will only still be around while in the Terminated state, until we're cleaned up! (wherein they are deleted! :o ), but their names can still be used of course! ^^
	postAbsentExpectedFileBasenames = None;  # like postUnexpectedFileBasenames but for things which we thought would be there but weren't!  (*cough* don't forget about creatures_engine_logfile.txt *cough*  XD   (and optional config files like password.cfg, language.cfg, etc.! )  )
	
	postStdout = None;  #if captureStdout was set to True when the engine started! :D
	postStderr = None;  #if captureStderr was set to True when the engine started! :D
	
	exitStatus = None;  #unix exit status of the engine! :D
	
	
	
	
	
	def __init__(self, roEngineTemplateDir, rwActiveSessionEngineDir=None, rwActiveSessionHomeDir=None, port=None, readInitialSkeletonConfigFileDataFromEngineTemplate=True):
		# {shhh, private things >,>
		self.waitLock = threading.Lock();
		self.cleaner = None;
		# }
		
		self.setLogToNonVerbose();
		
		
		self.setState(TransientLC2ESession.State_Unstarted);
		
		self.libfilebasenamesInSameDirAsEngine = ["lc2e-netbabel.so"];  #this lib has to be in the current dir (or just same dir as the engine?); idk why :p  (but the others seem fine to separate out! so might as well I guess..   *shrugs*  :>  )
		
		
		
		# All of the things has to be absolute pathnames here, since the engine will be starting in the session dir, not wherever we are 'cd'd to!  0,0
		self.roEngineTemplateDir = os.path.abspath(roEngineTemplateDir) if roEngineTemplateDir != None else None;
		
		
		if (rwActiveSessionEngineDir == None):  #ie, default :>
			self.setRWActiveSessionEngineDirToAutonameRightBeforeStart();
		else:
			self.setRWActiveSessionEngineDir(os.path.abspath(rwActiveSessionEngineDir));
		
		
		if (rwActiveSessionHomeDir == None):  #ie, default :>
			self.setRWActiveSessionHomeDirToAutocreateInsideEngineDirRightBeforeStart();
		else:
			self.setRWActiveSessionHomeDir(os.path.abspath(rwActiveSessionHomeDir));
		
		
		if (port == None):  #ie, default :>
			self.setPortToAutofindRightBeforeStart();
		else:
			self.setPort(port);
		
		
		if (readInitialSkeletonConfigFileDataFromEngineTemplate):
			self.readInitialSkeletonConfigFileDataFromEngineTemplate();
	#
	
	def loadDefaultsFromConfig(self, config):
		self.defaultAutoCreateSessionSuperSuperDirectory = config.transientSessionsSuperDirectory
		self.errorReportPackagesDirectory = config.errorReportPackagesDirectory
	#
	
	
	def setLogToVerbose(self, out=sys.stdout):
		def verboseLog(msg):
			self.defaultLog(msg);
			out.write("TransientLC2E: "+msg+"\n");
		self.log = verboseLog;
	def setLogToNonVerbose(self):
		self.log = self.defaultLog;
	def defaultLog(self, msg):
		self.capturedLog += msg + "\n\n";
	
	
	
	def setRWActiveSessionEngineDirToAutonameRightBeforeStart(self):
		self.rwActiveSessionEngineDir = None;
	def isRWActiveSessionEngineDirSetToAutonameRightBeforeStart(self):
		return self.rwActiveSessionEngineDir == None;
	
	def setRWActiveSessionEngineDir(self, rwActiveSessionEngineDir):
		self.log("Setting rwActiveSessionEngineDir to: "+(repr(rwActiveSessionEngineDir) if rwActiveSessionEngineDir != None else "<autocreate>")+"  ^^");
		self.rwActiveSessionEngineDir = rwActiveSessionEngineDir;
	
	def getRWActiveSessionEngineDir(self):
		return self.rwActiveSessionEngineDir;
	
	
	
	def setRWActiveSessionHomeDirToAutocreateInsideEngineDirRightBeforeStart(self):
		self.rwActiveSessionHomeDir = None;
	def isRWActiveSessionHomeDirSetToAutocreateInsideEngineDirRightBeforeStart(self):
		return self.rwActiveSessionHomeDir == None;
	
	def setRWActiveSessionHomeDir(self, rwActiveSessionHomeDir):
		self.log("Setting rwActiveSessionHomeDir to: "+(repr(rwActiveSessionHomeDir) if rwActiveSessionHomeDir != None else "<autocreate>")+"  ^^");
		self.rwActiveSessionHomeDir = rwActiveSessionHomeDir;
	
	def getRWActiveSessionHomeDir(self):
		return self.rwActiveSessionHomeDir;
	
	
	
	def getMachineConfig(self):
		if (self.machineConfig == None):
			self.machineConfig = {};
		return self.machineConfig;
	def getUserConfig(self):
		if (self.userConfig == None):
			self.userConfig = {};
		return self.userConfig;
	def getServerConfig(self):
		if (self.serverConfig == None):
			self.serverConfig = {};
		return self.serverConfig;
	def getPasswordConfig(self):
		if (self.passwordConfig == None):
			self.passwordConfig = {};
		return self.passwordConfig;
	def getLanguageConfig(self):
		if (self.languageConfig == None):
			self.languageConfig = {};
		return self.languageConfig;
	
	
	
	def loadCreaturesFilesystemIntoMachineConfigAsThePrimaryReadwriteFilesystem(self, creaturesFilesystem):
		self.loadCreaturesFilesystemIntoMachineConfig(creaturesFilesystem, None);
	
	def loadCreaturesFilesystemIntoMachineConfigAsTheAuxiliaryReadonlyFilesystem(self, creaturesFilesystem):
		"""Technically the engine supports more than one "Auxiliary" filesystem, but I don't think it does in practice X'D  (hence why the RO datas has to be merged into packs ;; )"""
		# Todo: set "Auxiliary 2 Images Directory" specificallies ???
		self.loadCreaturesFilesystemIntoMachineConfig(creaturesFilesystem, 1);
	
	def loadCreaturesFilesystemIntoMachineConfig(self, creaturesFilesystem, auxnum):
		"""
		Loads all the 'Xyz Directory' config keys in from the CreaturesFilesystem object ^_^
		This is something you HAS ta call, otherwise there will be no data directories! D:
		
		The first arg is the CreaturesFilesystem instance,
		and the second arg is an integer,
			None makes for "Bootstrap Directory", "Images Directory", etc.
			1 makes for "Auxiliary 1 Bootstrap Directory", "Auxiliary 1 Images Directory", etc.
			2 makes for "Auxiliary 2 Bootstrap Directory", "Auxiliary 2 Images Directory", etc.
			etc.  :>
		"""
		
		a = "Auxiliary "+repr(auxnum)+" " if auxnum != None else "";
		
		if (self.machineConfig == None):
			self.machineConfig = {};
		
		self.machineConfig[a+"Main Directory"] = creaturesFilesystem.Main_Directory;
		self.machineConfig[a+"Backgrounds Directory"] = creaturesFilesystem.Backgrounds_Directory;
		self.machineConfig[a+"Body Data Directory"] = creaturesFilesystem.Body_Data_Directory;
		self.machineConfig[a+"Bootstrap Directory"] = creaturesFilesystem.Bootstrap_Directory;
		self.machineConfig[a+"Catalogue Directory"] = creaturesFilesystem.Catalogue_Directory;
		self.machineConfig[a+"Creature Database Directory"] = creaturesFilesystem.Creature_Database_Directory;
		self.machineConfig[a+"Exported Creatures Directory"] = creaturesFilesystem.Exported_Creatures_Directory;
		self.machineConfig[a+"Genetics Directory"] = creaturesFilesystem.Genetics_Directory;
		self.machineConfig[a+"Images Directory"] = creaturesFilesystem.Images_Directory;
		self.machineConfig[a+"Journal Directory"] = creaturesFilesystem.Journal_Directory;
		self.machineConfig[a+"Overlay Data Directory"] = creaturesFilesystem.Overlay_Data_Directory;
		self.machineConfig[a+"Resource Files Directory"] = creaturesFilesystem.Resource_Files_Directory;
		self.machineConfig[a+"Sounds Directory"] = creaturesFilesystem.Sounds_Directory;
		self.machineConfig[a+"Users Directory"] = creaturesFilesystem.Users_Directory;
		self.machineConfig[a+"Worlds Directory"] = creaturesFilesystem.Worlds_Directory;
	#
	
	
	def extractCreaturesFilesystemFromMachineConfigAsThePrimaryReadwriteFilesystem(self):
		return self.extractCreaturesFilesystemFromMachineConfig(None)
	def extractCreaturesFilesystemFromMachineConfigAsTheAuxiliaryReadonlyFilesystem(self):
		return self.extractCreaturesFilesystemFromMachineConfig(1)
	
	def extractCreaturesFilesystemFromMachineConfig(self, auxnum):
		a = "Auxiliary "+repr(auxnum)+" " if auxnum != None else "";
		
		creaturesFilesystem = CreaturesFilesystem()
		creaturesFilesystem.Main_Directory = self.machineConfig[a+"Main Directory"]
		creaturesFilesystem.Backgrounds_Directory = self.machineConfig[a+"Backgrounds Directory"]
		creaturesFilesystem.Body_Data_Directory = self.machineConfig[a+"Body Data Directory"]
		creaturesFilesystem.Bootstrap_Directory = self.machineConfig[a+"Bootstrap Directory"]
		creaturesFilesystem.Catalogue_Directory = self.machineConfig[a+"Catalogue Directory"]
		creaturesFilesystem.Creature_Database_Directory = self.machineConfig[a+"Creature Database Directory"]
		creaturesFilesystem.Exported_Creatures_Directory = self.machineConfig[a+"Exported Creatures Directory"]
		creaturesFilesystem.Genetics_Directory = self.machineConfig[a+"Genetics Directory"]
		creaturesFilesystem.Images_Directory = self.machineConfig[a+"Images Directory"]
		creaturesFilesystem.Journal_Directory = self.machineConfig[a+"Journal Directory"]
		creaturesFilesystem.Overlay_Data_Directory = self.machineConfig[a+"Overlay Data Directory"]
		creaturesFilesystem.Resource_Files_Directory = self.machineConfig[a+"Resource Files Directory"]
		creaturesFilesystem.Sounds_Directory = self.machineConfig[a+"Sounds Directory"]
		creaturesFilesystem.Users_Directory = self.machineConfig[a+"Users Directory"]
		creaturesFilesystem.Worlds_Directory = self.machineConfig[a+"Worlds Directory"]
		return creaturesFilesystem
	#
	
	
	
	
	def readInitialSkeletonConfigFileDataFromEngineTemplate(self):
		"""
		Read in basic skeleton config in from the files in self.roEngineTemplateDir  ^_^
		"""
		
		def readConf(fileBasename, originalDict):
			p = os.path.join(self.roEngineTemplateDir, fileBasename);  #NOTE the different dir here compared with readPostConf! :>
			
			if (os.path.lexists(p)):
				self.log("Reading skeleton config from: "+repr(p));
				
				c = readallText(p);
				newstuff = parseCreaturesConfig(c);
				
				if (originalDict == None):
					return newstuff;
				else:
					originalDict.update(newstuff);
					return originalDict;
			else:
				self.log("Skipping non-existant skeleton config file: "+repr(p));
				return originalDict;
		
		self.machineConfig = readConf("machine-skel.cfg", self.machineConfig);
		self.userConfig = readConf("user-skel.cfg", self.userConfig);
		self.serverConfig = readConf("server-skel.cfg", self.serverConfig);
		self.passwordConfig = readConf("password-skel.cfg", self.passwordConfig);
		self.languageConfig = readConf("language-skel.cfg", self.languageConfig);
	#
	
	
	
	
	def setPort(self, port):
		if (not (port == None or isinstance(port, int) or isinstance(port, long))):
			raise TypeError("Wrong type for port, should be an integer!  Instead got a "+repr(type(port))+"  ;_;");
		
		self.log("Setting port to: "+(repr(port) if port != None else "<autofind>")+"  ^^");
		
		self.getUserConfig()["Port"] = repr(port) if port != None else None;
	
	def setPortToAutofindRightBeforeStart(self):
		"note: this is the default ^_^"
		self.setPort(None);
	def isPortSetToAutofindRightBeforeStart(self):
		return self.getPort() == None;
	
	def getPort(self):
		"note: if it was set to auto-find (setPortToAutofindRightBeforeStart()), then you can use this after the engine has been started to figure out which port it's using! ^w^"
		
		if (self.userConfig == None):
			return None;
		
		p = self.userConfig.get("Port");  #not being there should count same as == None because autofind is a nice default /thinks :>'
		return int(p) if p != None else None;
	
	def setAllowNetworkCaosConnections(self, insecureConnectionsEnabled):
		if (insecureConnectionsEnabled):
			self.getUserConfig()["PortSecurity"] = "0";
		else:
			self.getUserConfig()["PortSecurity"] = "1";
	
	def isAllowingNetworkCaosConnections(self):
		if (self.userConfig == None or not "PortSecurity" in self.userConfig):
			raise Exception("I dunno!  It hasn't been configured yet! :P");
		
		if (self.userConfig["PortSecurity"] == "0"):
			return True;
		elif (self.userConfig["PortSecurity"] == "1"):
			return False;
		else:
			raise Exception("Config error I think; PortSecurity should be either 0 or 1  (right?) ;_;");
	
	
	
	def setPrimaryGameName(self, primaryGameName):
		"""eg, setPrimaryGameName("Docking Station", "Creatures 3")  :> """
		
		self.log("Setting primary game name to: "+repr(primaryGameName));
		
		self.getMachineConfig()["Game Name"] = primaryGameName;
	
	def setAuxiliaryGameName(self, auxiliaryGameName):
		"""eg, setAuxiliaryGameName("Creatures 3")  :> """
		
		self.log("Setting auxiliary game name to: "+repr(auxiliaryGameName));
		
		self.getMachineConfig()["Win32 Auxiliary Game Name 1"] = auxiliaryGameName;  #no earthly clue why "Win32" is in there XD'?!
	
	def getPrimaryGameName(self):
		if (self.machineConfig == None):
			return None;
		
		return self.machineConfig.get("Game Name");   #get(), as opposed to [], returns None instead of raising KeyError  ^w^
	
	def getAuxiliaryGameName(self):
		if (self.machineConfig == None):
			return None;
		
		return self.machineConfig.get("Win32 Auxiliary Game Name 1");
	
	
	# Todo: more structured config things, mayhaps? :>?
	
	
	
	
	
	
	
	def _errWrongState(self):
		return TransientLC2ESessionStateException("It's in the wrong state! ;_;   (it is currently "+TransientLC2ESession.fmtstate(self.state)+" ;; )");
	
	
	def start(self, creator, hidden, name=None, description=None, icon=None):
		"""
		Start the lc2e engine!! :D!
		+ If this *doesn't* throw/raise an error, then it will be properly in the Running state ^^'
		
		creator, name description, icon are from the publishing protocol :3
		so creator is None for a user-made world, or the name of the tool for an automatic world (eg, TryAgent or RunCAOS)
		"""
		
		if (self.state != TransientLC2ESession.State_Unstarted):
			raise self._errWrongState();
		
		
		
		# Finish configuring! :D
		if (self.isPortSetToAutofindRightBeforeStart()):
			self.log("Autofinding port! :D");
			self.autoFindAndSetPort();
		
		if (self.isRWActiveSessionEngineDirSetToAutonameRightBeforeStart()):
			self.log("Autocreating session engine dir! :D");
			self.autoFindAndCreateSessionEngineDir();
			autocreatedEngineDir = True;
		else:
			autocreatedEngineDir = False;
		
		if (self.isRWActiveSessionHomeDirSetToAutocreateInsideEngineDirRightBeforeStart()):
			self.log("Autocreating session home dir! :D");
			self.autoCreateSessionHomeDir();
			autocreatedHomeDir = True;
		else:
			autocreatedHomeDir = False;
		
		
		
		
		# Publishing protocol! :D
		d = os.path.join(UserDir, "running")
		if (not os.path.isdir(UserDir)):
			os.mkdir(UserDir)
		if (not os.path.isdir(d)):
			os.mkdir(d)
		
		
		
		while True:
			publishingProtocolFile = os.path.join(d, str(Random().randint(0, 2147483647)))
			
			if (not os.path.lexists(publishingProtocolFile)):
				writeallText(publishingProtocolFile, "", overwrite=False)  #quickly as we race to the race condition as unix requires x'D
				
				extraInfo = {
					"creator": creator
				}
				
				if (name != None):
					extraInfo["name"] = name
				
				if (description != None):
					extraInfo["description"] = description
				
				if (icon != None):
					extraInfo["icon"] = icon
				
				
				rwcfs = self.extractCreaturesFilesystemFromMachineConfigAsThePrimaryReadwriteFilesystem()
				
				wd = rwcfs.Worlds_Directory
				if (wd != None and os.path.isdir(wd)):
					extraInfo["worldnames"] = os.listdir(wd)
				
				
				
				c = {
					"e6b02a88-7311-4a27-bbb7-d8f3a2d4e353": {
						"caosInjectionType": "tcp",
						"caosInjectionPort": self.getPort(),
						"caosInjectionHosts": ["0.0.0.0"] if self.isAllowingNetworkCaosConnections() else ["127.0.0.1"],
						"hidden": hidden,
						"rwdata": encodeCreaturesFilesystemForPublishingProtocol(rwcfs),
						"rodata": encodeCreaturesFilesystemForPublishingProtocol(self.extractCreaturesFilesystemFromMachineConfigAsTheAuxiliaryReadonlyFilesystem())
					},
					
					"2424f4d5-4888-421d-bd19-ba3d4067598d": extraInfo
				}
				
				writeallText(publishingProtocolFile, json.dumps(c, sort_keys=True, indent=4), overwrite=True)
				
				break
		#
		
		self.publishingProtocolFile = publishingProtocolFile
		
		
		
		# (important that registering cleaners for the just-created session dir comes right after making it ^^   since _actuallyStartXD() and autoFindAndSetPort() could fail/raise-exceptions! ;; )
		# Register an atexit and garbage collection hooks to clean up the state if somepony forgets to and the python virtual machine terminates ;3
		
		# Create a separate cleaner object which will be registered as a garbage collection listener here also, to same effect if we learn this object becomes lost *before* python actually terminates ;3
		self.cleaner = _lc2eSessionCleaner(self.rwActiveSessionEngineDir if autocreatedEngineDir else None, self.rwActiveSessionHomeDir if autocreatedHomeDir else None, publishingProtocolFile);  #PASS ALL THE THINGS NEEDED FOR CLEANING :>    (which turns out to just be the session dir XD)
		self.cleaner.registerAsGCListener();
		self.cleaner.registerAsAtExitHook();
		
		
		try:
			self._actuallyStartXD();
		except:
			self.cleaner.actuallyCleanUpXD();
			self.setState(TransientLC2ESession.State_CleanedUpNeverProperlyStarted);  #Always good to set state after cleaning up Ithinks, in case the cleanup fails XD'  :>
			raise;  #re-raise the exception! :>
		
		
		self.setState(TransientLC2ESession.State_Running);  #don't mark it as running unless that succeeded YD
		
		
		# Start a thread to wait on the process and promptly switch state to Terminated as soon as the engine terminated! ^w^   (if it hasn't already! Ack!)
		processWaiterThread = threading.Thread(target=self.waitForEngineToTerminate, name="TransientLC2E Child Process Waiter");
		processWaiterThread.setDaemon(True);  #not an important thread >>
		processWaiterThread.start();
	#
	
	def autoFindAndSetPort(self):
		"Note: this is automatically called by start() if isPortSetToAutofindRightBeforeStart() is true, *right* before execution, to minimize chances of some other process snagging out port >,> xD'"
		
		# Try random numbers for awhile :>
		r = random.Random(); #I checked; it's initialized with different seeds or whatnot by default each construction ^w^   (so we all (python processes and/or TransientLC2ESession instances within a python process) won't all be trying the exact same "random" sequence each time! XD''! )
		for _ in xrange(1000):
			port = r.randint(49152, 65535);  #this is the official range ICANN specifies for randomly/automatically XD' picking ports, I think!  Yay standards! :D! (so it's supposed to not conflict with things that rigidly *need* a certain port to be available!!)    (there are exactly one fourth of all ports in this range! :D )
			if (self._tryAcquireServerPort(port)):
				self.setPort(port);
				return;
		
		# If ALLLLLllll those were taken, just TRY ALL THE PORTS T-T
		for port in xrange(49152, 65535):
			if (_tryAcquireServerPort(port)):
				self.setPort(port);
				return;
		
		raise Exception("All ICANN dynamic/private ports ( [49152-65536) ) were taken! D:");
	#
	def _tryAcquireServerPort(self, port):
		# returns true if successful, false if port unavailable, or raises something if a different error occurs
		s = None;
		try:
			s = socket.socket(); #default  Internet class,  TCP (server or client) socket
			s.bind(('localhost', port));
		except socket.error, exc:
			s.close();
			if (exc.errno == errno.EADDRINUSE):  #Address already in use
				return False;
			else:
				raise;
		else:
			s.close();
			return True;
	#
	
	def autoFindAndCreateSessionEngineDir(self, superDir=Default):
		"Note: this is automatically called by start() if self.isRWActiveSessionEngineDirSetToAutonameRightBeforeStart() is true, *right* before execution, for convenience, and so it will be cleaned up as part of the normal cleanup cycle if something goes wrong ^_^"
		
		if (superDir == Default):
			superDir = self.defaultAutoCreateSessionSuperSuperDirectory
		
		self.setRWActiveSessionEngineDir(getUnusedFileSimilarlyNamedTo(superDir, "autonamed-transient-lc2e-session"));
		
		os.mkdir(self.getRWActiveSessionEngineDir(), 0755);
	#
	
	def autoCreateSessionHomeDir(self, parentDir=None):
		"Note: this is automatically called by start() if self.isRWActiveSessionHomeDirSetToAutocreateInsideEngineDirRightBeforeStart() is true, *right* before execution, for convenience, and so it will be cleaned up as part of the normal cleanup cycle if something goes wrong ^_^"
		
		if (parentDir == None):
			parentDir = self.getRWActiveSessionEngineDir();
		
		d = os.path.join(parentDir, "fakehome");
		
		os.mkdir(d, 0755);
		os.mkdir(os.path.join(d, ".config"), 0755);
		os.symlink(os.path.join(os.getenv("HOME"), ".config", "pulse"), os.path.join(d, ".config", "pulse"));
		
		self.setRWActiveSessionHomeDir(d);
	#
	
	
	
	
	
	def _actuallyStartXD(self):   #yes that's an emoticon in the function name      ..what?  I'm a puppy! ^w^
		
		# Okay so, FIRST
		# we link in the engine executable and lib[s] ^_^
		engineFilenamesToLinkIn = ["lc2e"] + self.libfilebasenamesInSameDirAsEngine;
		
		self.log("Symlinking in the engine files and folders! :D");
		
		# Actually make teh links! :D
		for n in engineFilenamesToLinkIn:
			s = os.path.join(self.roEngineTemplateDir, n);
			d = os.path.join(self.rwActiveSessionEngineDir, n);
			
			if (os.path.lexists(d)):
				raise Exception("Symlink we tried to make already exists!? D:   ("+repr(s)+" -> "+repr(d)+")");
			
			os.symlink(os.path.abspath(s), d);
		
		
		
		
		
		
		
		# And then figure out the library dirs and environment stuff! :D
		libdirs = filter(lambda bn: bn.startswith("lib"), os.listdir(self.roEngineTemplateDir));
		libdirs = map(lambda bn: os.path.join(self.roEngineTemplateDir, bn), libdirs);  #make them full paths! ^_^
		libdirs = filter(lambda d: os.path.isdir(d), libdirs);
		
		if (any(map(lambda p: ":" in p, libdirs))):
			# Try the realpaths, maybe they're better! ;_;
			libdirs = map(os.path.realpath, libdirs);
			
			if (any(map(lambda p: ":" in p, libdirs))):
				# Nope! T-T
				raise Exception("There are colons in the lib dirs, that makes UNIX explode D:  (because colons separate shared-library dirs in LD_LIBRARY_PATH and there isn't an escape syntax to my knowledge >,> )     Library dirs: "+repr(libdirs));
		
		# Add the (future) current dir (eg, for lc2e-netbabel.so and others if someday there are others X3 )  ^_^
		allLibDirs = ["."] + libdirs;  #Note: "." will be a different place for the engine (rwActiveSessionEngineDir), when we start it in rwActiveSessionEngineDir ;>
		
		LD_LIBRARY_PATH = ":".join(allLibDirs);
		
		
		
		
		# Get the X11 display for, you know, graphics! XD   (that's important, don't forget that XD''')
		x11Display = os.getenv("DISPLAY");
		if (x11Display == None):
			raise Exception("There is no X11 display! D:   LC2E won't run without graphics!!  (although that might actually be useful for servers or stuff 8> )");
		
		
		
		
		# Write config files! :D!
		
		self.log("Writing engine configuration files! :D");
		
		def writeConf(fileBasename, configDict):
			if (configDict == None):
				return; #skip! ^w^
			else:
				writeallText(os.path.join(self.rwActiveSessionEngineDir, fileBasename), serializeCreaturesConfig(configDict), overwrite=False);
		
		writeConf("machine.cfg", self.machineConfig);
		writeConf("user.cfg", self.userConfig);
		writeConf("server.cfg", self.serverConfig);
		writeConf("password.cfg", self.passwordConfig);
		writeConf("language.cfg", self.languageConfig);
		
		
		
		
		# ACTUALLY START! :D!!!
		exe = os.path.abspath(os.path.join(self.rwActiveSessionEngineDir, "lc2e"));   #EXEcutable in the general sense, not Microsoft Windows format XD'   (kind of like Dynamically Linked Library, or High-Definition DVD, etc.c.   .... #when companies grab generic names for their products >_>  XD' )
		
		env = {"LD_LIBRARY_PATH": LD_LIBRARY_PATH, "DISPLAY": x11Display, "HOME": self.rwActiveSessionHomeDir};
		
		cwd = self.rwActiveSessionEngineDir;
		
		self.log("ACTUALLY STARTING THE ENGINE!! \\o/");
		self.log(repr(exe));
		self.log("\tCWD: "+repr(cwd));
		self.log("\tENV: "+json.dumps(env, indent=1, sort_keys=True));
		
		#None (python subprocess.Popen) = Inherit (java.lang.Process)  ^_^
		stdin = subprocess.PIPE if (self.dataToFeedToStdin != None and len(self.dataToFeedToStdin) > 0) else None;
		stdout = subprocess.PIPE if self.captureStdout else None;
		stderr = subprocess.PIPE if self.captureStderr else None;
		
		self.process = subprocess.Popen([exe], executable=exe, cwd=cwd, env=env, stdin=stdin, stdout=stdout, stderr=stderr);   #the first arg here is arg0, which, as per Unix, is what the process will know itself as :>   (which is just exactly the same as the actual executable (symlink!) here XD   (but we still has to give it or things could explode D: )    the executable= part is prolly superfluous..but I like being explicits ^^' )
		
		if (stdin != None):
			def feeder():
				self.process.stdin.write(self.dataToFeedToStdin);
				self.process.stdin.close();
			
			thread = threading.Thread(target=feeder, name="Dumper");
			thread.daemon = True;
			thread.start();
		
		def spawnCollector(source, store, buffsize=4096):
			def run():
				captured = bytearray();
				
				while True:
					b = source.read(buffsize);
					if (len(b) == 0):  # zero-length read means EOF in python and C but not Java :P
						store(str(captured));  #meh, python likes str's over bytearrays, ohwells :P
						source.close();
						return;
					else:
						captured += b;
			#
			
			thread = threading.Thread(target=run, name="Collector");
			thread.daemon = True;
			thread.start();
			return thread;
		#
		
		if (stdout != None):
			def setstdout(x): self.postStdout = x;
			self.stdoutCollector = spawnCollector(self.process.stdout, setstdout);
		
		if (stderr != None):
			def setstderr(x): self.postStderr = x;
			self.stderrCollector = spawnCollector(self.process.stderr, setstderr);
	#
	
	
	
	
	def setState(self, newState):
		self.log("State set to: "+TransientLC2ESession.fmtstate(newState));
		
		self.state = newState;
		
		if (self.cleaner != None):
			self.cleaner.state = newState;
		
		
		if (newState == TransientLC2ESession.State_Terminated):
			self._reapThingsAfterTermination();   # :D
	#
	
	
	def waitForEngineToTerminate(self):
		# Todo add an optional timeout parameter? :p
		
		# I didn't add locks here..and this is what happened:
		#print("WAITING: STATE IS "+TransientLC2ESession.fmtstate(self.state));
		#(water thread started and called this in self.start())
		#(main thread called this in main())
		#	"WAITING: STATE IS running"
		#	"WAITING: STATE IS running"
		# Classic. Threading. Bug.  X'D'''
		
		
		self.waitLock.acquire();
		
		try:
			if (self.state == TransientLC2ESession.State_Running):
				pass;
			elif (self.state == TransientLC2ESession.State_Terminated or self.state == TransientLC2ESession.State_CleanedUp or self.state == TransientLC2ESession.State_CleanedUpNeverProperlyStarted):
				return;
			else:
				raise self._errWrongState();
			
			
			self.exitStatus = self.process.wait();   #I checked!  It does return instantly if the process completes/terminates SUPERINCREDIBLYFAST before we even call this!!  ^w^
			
			self.log("LC2E terminated!, exit status: "+repr(self.exitStatus));
			
			
			# If we don't compleeeeteelyyyy wait for these to be all the dones, we can't guarantee that we'll have postStdout/postStderr! ;-;
			if (self.captureStdout):
				self.stdoutCollector.join();
			
			if (self.captureStderr):
				self.stderrCollector.join();
			
			
			self.setState(TransientLC2ESession.State_Terminated);  #will reap the things ^_^
		finally:
			self.waitLock.release();
	#
	
	def _reapThingsAfterTermination(self):
		# Read post-log file :>
		self.log("Reading the logfile the engine wrote, for explorative purposes :>");
		
		logfile = os.path.join(self.getRWActiveSessionEngineDir(), "creatures_engine_logfile.txt");
		if (os.path.isfile(logfile)):
			self.postLogfile = readallText(logfile);
		else:
			self.postLogfile = None;
		
		
		# Read post-config files :>
		self.log("Re-reading the config files the engine rewrote, for explorative purposes :>");
		
		def readPostConf(fileBasename):
			p = os.path.join(self.getRWActiveSessionEngineDir(), fileBasename);  #NOTE the different dir here compared with readConf! :>
			if (os.path.lexists(p)):
				c = readallText(p);
				
				try:
					return parseCreaturesConfig(c), c;
				except:
					print("Error parsing "+fileBasename+" generated by the engine in _reapThingsAfterTermination(), dumping contents here between equals sign bars:")
					print("============================================================")
					print(c)
					print("============================================================")
					raise
			else:
				return None, None;
		
		self.postMachineConfig, self.postMachineConfigRaw = readPostConf("machine.cfg");
		self.postUserConfig, self.postUserConfigRaw = readPostConf("user.cfg");
		self.postServerConfig, self.postServerConfigRaw = readPostConf("server.cfg");
		self.postPasswordConfig, self.postPasswordConfigRaw = readPostConf("password.cfg");
		self.postLanguageConfig, self.postLanguageConfigRaw = readPostConf("language.cfg");
		
		
		self.log("Checking to see if there are any *other* files we weren't expecting to be there! :o");
		expectedFileBasenames = set(["lc2e"] + self.libfilebasenamesInSameDirAsEngine + ["machine.cfg", "user.cfg", "server.cfg", "password.cfg", "language.cfg"] + ["creatures_engine_logfile.txt"]);
		if (os.path.dirname(os.path.abspath(self.getRWActiveSessionHomeDir())) == os.path.abspath(self.getRWActiveSessionEngineDir())):
			expectedFileBasenames.add(os.path.basename(self.getRWActiveSessionHomeDir()));
		
		actualFileBasenames = set(os.listdir(self.getRWActiveSessionEngineDir()));
		
		self.postUnexpectedFileBasenames = actualFileBasenames - expectedFileBasenames;  #don't ya love operators! 8>    (when they are mapped, that is >,>    (*grumbles at lack of "+" for sets in python*   X'D )
		self.postAbsentExpectedFileBasenames = expectedFileBasenames - actualFileBasenames;
		
		
		
		
		
		if (self.didEngineCrash()):
			# Note: musht be called afterwards, so it has alllll the happy postXYZ things! ^^
			self._produceCrashReportPackage();
	#
	
	def _produceCrashReportPackage(self):
		if (self.errorReportPackagesDirectory != None):
			crashReportPackageDir = os.path.join(self.errorReportPackagesDirectory, os.getenv("USER")+"@"+socket.gethostname()+":"+repr(time.time()));
			if (os.path.lexists(crashReportPackageDir)):
				# It already exists!? ;_;!?
				# ohwell; uhh, just silently do nothing.  If things are happening so much that multiple TransientLC2ESession's are doing things at the same *microsecond* (or milli or nano, or whatever precision time.time() happens to be on the current OS ^^' ), then there are many other things that would break XD''   Like checking for unique filenames *then* creating it (in which two people could 'discover' the same available name, then both try to create a file with that name ><!   Oh non-holistic operating systems..there are so many issues with yall X'D )
				return;
			
			os.mkdir(crashReportPackageDir);
			
			
			if (self.state == TransientLC2ESession.State_CleanedUpNeverProperlyStarted):
				writeallText(os.path.join(crashReportPackageDir, "never-started"), ";_;");
			
			else:
				writeallText(os.path.join(crashReportPackageDir, "exit-status"), repr(self.exitStatus));
				
				
				writeallText(os.path.join(crashReportPackageDir, "transientlc2e.log"), self.capturedLog);
				
				
				if (self.dataToFeedToStdin != None):
					writeallText(os.path.join(crashReportPackageDir, "provided-stdin"), self.dataToFeedToStdin);
				else:
					writeallText(os.path.join(crashReportPackageDir, "didnt-provide-stdin"), "nope");
				
				if (self.captureStdout):
					if (self.postStdout == None): raise AssertionError();
					writeallText(os.path.join(crashReportPackageDir, "stdout.out"), self.postStdout);
				else:
					writeallText(os.path.join(crashReportPackageDir, "didnt-capture-stdout"), "nope ,_,");
				
				if (self.captureStderr):
					if (self.postStderr == None): raise AssertionError();
					writeallText(os.path.join(crashReportPackageDir, "stderr.out"), self.postStderr);
				else:
					writeallText(os.path.join(crashReportPackageDir, "didnt-capture-stderr"), "nope ,_,");
				
				
				if (self.postLogfile == None):
					writeallText(os.path.join(crashReportPackageDir, "there-was-no-creatures_engine_logfile.txt"), "nope");
				else:
					writeallText(os.path.join(crashReportPackageDir, "creatures_engine_logfile.txt"), self.postLogfile);
				
				
				writeallText(os.path.join(crashReportPackageDir, "unexpected-files"), repr(self.postUnexpectedFileBasenames));
				writeallText(os.path.join(crashReportPackageDir, "absent-expected-files"), repr(self.postAbsentExpectedFileBasenames));
				
				
				
				
				def logAConfig(basename, preDict, postDict, postSer):
					if (preDict == None):
						writeallText(os.path.join(crashReportPackageDir, "provided-"+basename+"-not-given"), "nope :p");
					else:
						preSer = serializeCreaturesConfig(preDict);  #will produce exactly the same output as it did when we originally created the file to give to the engine (I DO SO HOPE XD'')
						writeallText(os.path.join(crashReportPackageDir, "provided-"+basename), preSer);
						writeallText(os.path.join(crashReportPackageDir, "provided-"+basename+".pyrepr"), repr(preDict));
					
					if (postSer == None):
						writeallText(os.path.join(crashReportPackageDir, "reaped-"+basename+"-not-detected"), "nope ._.");
					else:
						if (preDict != None and postSer == preSer):
							writeallText(os.path.join(crashReportPackageDir, "reaped-"+basename+"-was-EXACTLY-equal-to-provided"), "yup!");
						else:
							writeallText(os.path.join(crashReportPackageDir, "reaped-"+basename), postSer);
							writeallText(os.path.join(crashReportPackageDir, "reaped-"+basename+".pyrepr"), repr(postDict));
				
				logAConfig("machine.cfg", self.machineConfig, self.postMachineConfig, self.postMachineConfigRaw);
				logAConfig("user.cfg", self.userConfig, self.postUserConfig, self.postUserConfigRaw);
				logAConfig("server.cfg", self.serverConfig, self.postServerConfig, self.postServerConfigRaw);
				logAConfig("password.cfg", self.passwordConfig, self.postPasswordConfig, self.postPasswordConfigRaw);
				logAConfig("language.cfg", self.languageConfig, self.postLanguageConfig, self.postLanguageConfigRaw);
			
			
			self.log("Error report package written to: "+repr(crashReportPackageDir));
	#
	
	
	
	
	
	def checkEngineTerminatedOrCleanedUp(self):
		if (self.state != TransientLC2ESession.State_Terminated and self.state != TransientLC2ESession.State_CleanedUp):
			raise self._errWrongState();
	
	
	def didEngineCrash(self):
		self.checkEngineTerminatedOrCleanedUp();
		
		return self.exitStatus != 1;  #apparently LC2E return a failure exit code (ie, anything but 0 XD, as per POSIX) even when it completes properly! o,0   Ohwells! Just go with it! XD
	#
	
	
	
	def runcaos(self, caoscode):
		if (self.state != TransientLC2ESession.State_Running):
			raise self._errWrongState();
		
		try:
			s = socket.socket();
			s.connect(("localhost", self.getPort()));
			
			try:
				s.sendall(caoscode+"\r\nrscr\r\n");  #we could use the fileything from s.makefile() but prolly fasters to use this nice thing here :3    (we are lazy to use the makefile down below >,> )
				f = s.makefile();
				response = f.read();
			
			finally: #ie, make SURE this is called, even if it throws an exception! ;D
				s.close();
			
			return response;
		except socket.error, e:
			if (e.errno == errno.ECONNREFUSED):
				raise TransientLC2ESessionCAOSConnectionRefused();
			else:
				raise;
	#
	
	
	def waitForEngineToBecomeCaosable(self):
		if (self.state != TransientLC2ESession.State_Running):
			raise self._errWrongState();
		
		while True:
			try:
				r = self.runcaos("setv va00 9  mulv va00 va00  outv va00");
			except TransientLC2ESessionCAOSConnectionRefused:
				pass;
			else:
				return;
			
			time.sleep(.1);
	#
	
	
	
	def quitWithoutSaving(self):
		#  ^_^
		self.runcaos("quit");
		self.waitForEngineToTerminate();
	
	def saveAndQuit(self):
		#  ^_^
		self.runcaos("save quit");
		self.waitForEngineToTerminate();
	
	
	def brutallyKillEngine(self):
		if (self.state != TransientLC2ESession.State_Running):
			raise self._errWrongState();
		
		os.kill(self.pid, 2);  #Signal 2 is SIGINT ("Interrupt" :> )   (ie, this is what the shell does when you press Ctrl-C in its terminal! :D )
		self.waitForEngineToTerminate();
	
	def viciouslyKillEngine(self):
		"I am traumatizing myself with these names T,T"
		
		if (self.state != TransientLC2ESession.State_Running):
			raise self._errWrongState();
		
		os.kill(self.pid, 9);  #Signal 9 is SIGKILL ie, vicious (unignorable signal!) ;_;
		self.waitForEngineToTerminate();
	
	
	
	def cleanUp(self):
		"Remove the transient instance directory and etc. etc.! ^w^"
		
		if (self.state != TransientLC2ESession.State_Terminated):
			raise self._errWrongState();
		
		self.cleaner.actuallyCleanUpXD();
		
		#Always good to set state to [completely-]cleaned-up after cleaning up Ithinks, in case the cleanup fails XD'  :>
		self.setState(TransientLC2ESession.State_CleanedUp);  #sets the cleaner's state too :3
	#
#

class TransientLC2ESessionStateException(Exception):
	pass;

class TransientLC2ESessionCAOSConnectionRefused(Exception):
	pass;



class _lc2eSessionCleaner(object):
	"""
	Note that this doesn't terminate the engine, so if we stop while it's still going, just leave it be and let the userpeoples worry about cleaning up the transient session directory and such X3
	
	TODO EXPLAIN WHY NECESSARY ;;''''
	"""
	
	
	state = None;
	
	# <All the things necessary for actually cleaning up! :D
	rwActiveSessionEngineDir = None;
	rwActiveSessionHomeDir = None;
	publishingProtocolFile = None
	# All the things necessary for actually cleaning up! :D >
	
	
	def __init__(self, rwActiveSessionEngineDir, rwActiveSessionHomeDir, publishingProtocolFile):
		self.rwActiveSessionEngineDir = rwActiveSessionEngineDir;
		self.rwActiveSessionHomeDir = rwActiveSessionHomeDir;
		self.publishingProtocolFile = publishingProtocolFile
	#
	
	
	
	def registerAsGCListener(self):
		registerGCListener(self, self.cleanUpIfNeeded);
	
	def registerAsAtExitHook(self):
		atexit.register(self.cleanUpIfNeeded);
	
	def cleanUpIfNeeded(self):
		if (self.state == TransientLC2ESession.State_Terminated):
			self.actuallyCleanUpXD();
			self.state = TransientLC2ESession.State_CleanedUp;  #also set by the actual session if that's what called us, but if not then we need to set it on ourselves! (BECAUSE THE SESSION IS GONNEEEEE! ;_;   x3 )
	#
	
	def actuallyCleanUpXD(self):
		# I assume exceptions/errors raised/thrown to atexit hook callers and garbage collection listeners (weakref callbacks) aren't problems and handled nicelies? ^^''?
		
		def unlinkIfThere(x):
			if (os.path.lexists(x) and (not os.path.isdir(x) or os.path.islink(x))):
				os.unlink(x);
		
		def rmdirIfThere(x):
			if (os.path.isdir(x)):
				os.rmdir(x);
		
		unlinkIfThere(self.publishingProtocolFile)
		
		if (self.rwActiveSessionHomeDir != None):
			d = self.rwActiveSessionHomeDir
			
			unlinkIfThere(os.path.join(d, ".config", "pulse"))
			rmdirIfThere(os.path.join(d, ".config"))
			
			unlinkIfThere(os.path.join(d, ".creaturesengine", "port"));
			rmdirIfThere(os.path.join(d, ".creaturesengine"));
			rmdirIfThere(d);
		
		if (self.rwActiveSessionEngineDir != None):
			d = self.rwActiveSessionEngineDir
			
			unlinkIfThere(os.path.join(d, ".config", "pulse"))
			rmdirIfThere(os.path.join(d, ".config"))
			
			# Just simply unlink/delete all the symlinks and plain files (creatures_engine_logfile.txt and rewritten config files)  ^_^
			for n in os.listdir(d):
				p = os.path.join(d, n);
				os.unlink(p);
			
			# Then get rid of the whole dir! :D
			rmdirIfThere(d);
	#
#



def encodeCreaturesFilesystemForPublishingProtocol(cfs):
	return {
		"Main": cfs.Main_Directory,
		"Backgrounds": cfs.Backgrounds_Directory,
		"Body Data": cfs.Body_Data_Directory,
		"Bootstrap": cfs.Bootstrap_Directory,
		"Catalogue": cfs.Catalogue_Directory,
		"Creature Galleries": cfs.Creature_Database_Directory,
		"My Creatures": cfs.Exported_Creatures_Directory,
		"Genetics": cfs.Genetics_Directory,
		"Images": cfs.Images_Directory,
		"Journal": cfs.Journal_Directory,
		"Overlay Data": cfs.Overlay_Data_Directory,
		"My Agents": cfs.Resource_Files_Directory,
		"Sounds": cfs.Sounds_Directory,
		"Users": cfs.Users_Directory,
		"My Worlds": cfs.Worlds_Directory
	}
#




# Creaturesey things! :D!!


# TODO: Catalogue file parsing and writing  -->  Allowing us to make code to AUTOMATICALLY RESOLVE THE CATALOGUE CONFLICTS WHICH CAUSE SEGFAULTS T_T   (eg, from merging C3 and DS)    :D!!


class CreaturesFilesystem(object):
	base = None;
	
	
	def __init__(self, base=None):
		if (base != None):
			base = os.path.abspath(base);
			
			self.base = base;
			self.configureForDefaults();
		#else the fields will be populated manually!
	#
	
	
	def configureForDefaults(self):
		base = self.base;  #shortness ^^
		
		# Standard creatures defaults! :D
		self.Main_Directory = os.path.join(base, "Main");                               # ????
		self.Backgrounds_Directory = os.path.join(base, "Backgrounds");                 # BLK background files :>
		self.Body_Data_Directory = os.path.join(base, "Body Data");                     # Attachment files :3
		self.Bootstrap_Directory = os.path.join(base, "Bootstrap");                     # Cos files! :D
		self.Catalogue_Directory = os.path.join(base, "Catalogue");                     # Catalogue files! ^_^
		self.Creature_Database_Directory = os.path.join(base, "Creature Galleries");    # ????
		self.Exported_Creatures_Directory = os.path.join(base, "My Creatures");         # Pray files :3
		self.Genetics_Directory = os.path.join(base, "Genetics");                       # GEN (genetics) and GNO (genetics annotation) files! :>
		self.Images_Directory = os.path.join(base, "Images");                           # C16 and S16 files! :D
		self.Journal_Directory = os.path.join(base, "Journal");                         # Journal text files! :D
		self.Overlay_Data_Directory = os.path.join(base, "Overlay Data");               # C16 and S16 files! :>
		self.Resource_Files_Directory = os.path.join(base, "My Agents");                # Pray files :3
		self.Sounds_Directory = os.path.join(base, "Sounds");                           # (MS)Wave (sfx) and Munge (music) files! :D
		self.Users_Directory = os.path.join(base, "Users");                             # ????
		self.Worlds_Directory = os.path.join(base, "My Worlds");                        # Serialized, zlib-compressed world memoryimages! :D
	#
	
	
	
	def readJournalFile(self, journalFile):
		"Returns None if and only if the file doesn't exist (raises exceptions otherwise :> )"
		
		jf = os.path.abspath(os.path.join(self.Journal_Directory, journalFile));
		
		if (not os.isfile(jf)):
			return None;
		else:
			return readallText(jf);
	#
	
	def writeJournalFile(self, journalFile, contents):
		"Write (overwrite if exists!) a journal file in the current session! ^w^"
		
		jf = os.path.abspath(os.path.join(self.Journal_Directory, journalFile));
		
		writeallText(journalFile, contents, overwrite=True);
	#
	
	
	def linkInPrimaryDirectory(self, extantToplevelDirectory, pathnameInThisFilesystem=None):
		"For linking in eg, the ENTIRE IMAGES/ FOLDER :O   :> "
		
		if (pathnameInThisFilesystem == None):
			pathnameInThisFilesystem = os.path.join(self.base, os.path.basename(extantToplevelDirectory));
		
		self.linkInAFileFailing(extantToplevelDirectory, pathnameInThisFilesystem);
	
	def linkInAgentFile(self, extantAgentFile):
		self.linkInAFileRenaming(extantAgentFile, self.Resource_Files_Directory);  #eg, "My Agents" :>
	def linkInExportedCreatureFile(self, extantCreatureFile):
		self.linkInAFileRenaming(extantCreatureFile, self.Exported_Creatures_Directory);  #eg, "My Creatures" :>
	def linkInWorld(self, extantWorldFolder):
		self.linkInAFileRenaming(extantWorldFolder, self.Worlds_Directory);  #eg, "My Worlds" :>
	
	
	
	def linkInWholeFolder_IgnoringConflicts(self, sourceFolder, destFolder):
		sourceFolder = os.path.abspath(sourceFolder);
		destFolder = os.path.abspath(destFolder);
		
		for n in os.listdir(sourceFolder):
			s = os.path.join(sourceFolder, n);
			d = os.path.join(destFolder, n);
			
			if (os.path.lexists(d)):
				continue;
			
			os.symlink(s, d);
	#
	
	def linkInWholeFolder_ErringOnConflicts(self, sourceFolder, destFolder):
		sourceFolder = os.path.abspath(sourceFolder);
		destFolder = os.path.abspath(destFolder);
		
		for n in os.listdir(sourceFolder):
			s = os.path.join(sourceFolder, n);
			d = os.path.join(destFolder, n);
			
			if (os.path.lexists(d)):
				raise Exception("AHHHHHH CONFLICT!!  WE DON'T LIKE CONFLICT!!  T_T    (conflict between source "+repr(s)+" and dest "+repr(d)+"  ;_; )");
			
			os.symlink(s, d);
	#
	
	def linkInWholeFolder_RenamingConflicts(self, sourceFolder, destFolder):
		sourceFolder = os.path.abspath(sourceFolder);
		destFolder = os.path.abspath(destFolder);
		
		for n in os.listdir(sourceFolder):
			s = os.path.join(sourceFolder, n);
			d = os.path.join(destFolder, n);
			
			if (os.path.lexists(d)):
				d = getUnusedFileSimilarlyNamedTo(os.path.dirname(d), n);
			
			os.symlink(s, d);
	#
	
	
	
	
	
	def linkInAFileRenaming(self, extantFile, directory):
		extantFile = os.path.abspath(extantFile);
		directory = os.path.abspath(directory);
		
		bn = os.path.basename(extantFile);
		
		newFile = getUnusedFileSimilarlyNamedTo(directory, bn);
		
		os.symlink(extantFile, newFile);
	#
	
	
	def linkInAFileFailing(self, extantFile, directory):
		extantFile = os.path.abspath(extantFile);
		directory = os.path.abspath(directory);
		
		bn = os.path.basename(extantFile);
		
		newFile = os.path.join(directory, bn);
		
		if (os.path.lexists(newFile)):
			raise Exception("File we're trying to link already exists with same name in destination directory! D:   (tried to link "+repr(extantFile)+" into "+repr(directory)+"  ;_; )");
		
		os.symlink(extantFile, newFile);
	#
#


# Not inside CreaturesFilesystem because it's used by other codes too ^^
def getUnusedFileSimilarlyNamedTo(directory, similarlyNamedToThisBasename):
	"Note: takes a Basename, returns a Pathname!"
	
	# If that name actually isn't taken up, then use that of course! :D
	f = os.path.join(directory, similarlyNamedToThisBasename);
	
	if (not os.path.lexists(f)):
		return os.path.abspath(f);
	
	
	# But if not then we'll haves to find an unused name >,>
	if ("." in similarlyNamedToThisBasename and similarlyNamedToThisBasename.rindex(".") == 0):   #and not starts with "." (which means hidden-file on unixen, not extension :3 )
		stemName, extension = similarlyNamedToThisBasename.rsplit(".", 1);
		suffix = "."+extension;
	else:
		stemName = similarlyNamedToThisBasename;
		suffix = "";
	
	i = 2;
	while True:
		f = os.path.join(directory, stemName+" "+repr(i)+suffix);
		
		if (not os.path.lexists(f)):
			return os.path.abspath(f);
		
		i += 1;
	
	# Never reaches this point (python integers don't overflow/wrap-around! :D  ..^^') it will just raise an exception someday when the pathname gets too long, if EVERYTHING IS TAKEN O,O   (or raise an exception like exponentially sooner, when the maximum number of files/dirs per dir is exceeded ^^' XD' )
#




# Config file syntax! :D
#	+ Just a bunch of lines of <key> + " " + <value> + linebreak  ^_^
#		+ The key and value can be quoted with double-quotes to allow spaces and special characters, or not! ^_^
#		+ Note: even if it is quoted, if a linebreak is inside a string, it will break (specifically, for values at least, it will just exactly stop reading it at the end of the line :3 )
#		+ Linebreaks *CAN* be *encoded* into strings, though!  Just use the escape syntax below! :D
#	+ Comments begin with "#" and last to the end of the line; they can happen anywhere in the file not just eg, at line start!! (although if it appears in a quoted string it will be part of the quotes!)   :D
#	+ Empty lines are ignored :3
#	+ Case SENSITIVE!
#	+ Non-quoted strings interpret backslashes and double-quotes as just normal parts of the string!  (there are no escapes inside non-quoted strings!)
#	
#	+ Note: the engine checks that non-auxiliary directories exist before startup! (but not auxiliary ones!) (is usefuls for figuring out syntax ;}  XD  )

# Config file escape codes! :D
#	\\	\
#	\"	"
#	\n	<LF>
#	\r	<CR>
#	\t	<TAB>
# 
# + Also, it is strict.  Any invalid escape codes produce a syntax error
# 
# Not config file escape codes!
#	+ I tried all individual lowercase latin letters and arabic numerals as escape codes, only the above work (which is enough! :> )
#	+ I tried \x## \u## \u#### \u######## \U######## (and \0 as mentioned above) with no success

ConfigFileEscapeCodeDict = {
	"\\": "\\",
	"\"": "\"",
	"n": "\n",
	"r": "\r",
	"t": "\t",
};


def parseCreaturesConfig(configFileContents):
	source = configFileContents;
	
	try:
		configDict = {};
		
		_Key = 0;
		_Value = 1;
		_LineEnd = 2;
		which = _Key;
		
		_BeforeString = 0;
		_InQuotedString = 1;
		_InQuotedString_InEscape = 2;
		_InNonquotedString = 3;
		_InComment = 4;
		where = _BeforeString;
		
		start = None;
		currKey = None;
		
		# Note: some of the "continue"s are superfluous; I just like being explicits sometimes ^^'
		
		
		def descapestr(s):
			if (not "\\" in s): #superfast check! :D
				# there are no escapes! we don't need to descape! :D
				
				#print("DEBUGPARSER) descapestr(): passthrough, no descaping! ^w^  "+repr(s));
				
				return s;
			else:
				# aw ._.  XD
				
				descapedStr = "";
				
				st = 0;  #can't use 'start', that would conflict! ><  X'D
				while True:
					#s.index would throw exception instead of returning special value (-1)  ;>'
					e = s.find("\\", st);  #can't use 'i', that would conflict! ><  X'D
					
					if (e == -1):
						break;
					else:
						if (st != e):  #ie, not-empty string between start of last run of clear text (st) and the next backslash (e)  ^w^
							if (st > e): raise AssertionError();
							descapedStr += s[st:e];
						
						if (not (e+1 < len(s))):
							raise AssertionError();  #we should never have been passed one with a trailing backslash! ;-;
						else:
							escapeCode = s[e+1];
							
							if (not escapeCode in ConfigFileEscapeCodeDict):
								raise Exception("Syntax error!: bad escape code "+repr(escapeCode)+" !");
							
							descapedStr += ConfigFileEscapeCodeDict[escapeCode];
							
							st = e+2;  #after the escape char (backslash) AND the escape code! :3   (which may be EOF, but that's okay, we check for that down there! and x[len(x):len(x)] is valid in python anyways, returning empty string! ^w^ )
				
				if (st != len(s)):  #ie, not-empty string between start of last run of clear text (st) and the end of the string!  ^w^
					if (st > len(s)): raise AssertionError();
					descapedStr += s[st:];
				
				#print("DEBUGPARSER) descapestr(): descaped "+repr(s)+" into "+repr(descapedStr)+"  :D");
				
				return descapedStr;
		
		
		def consumestr(s, descapeit):
			if (which == _Key):
				_currKey = descapestr(s) if descapeit else s;
				_which = _Value;
			
			elif (which == _Value):
				value = descapestr(s) if descapeit else s;
				if (currKey in configDict):
					raise Exception("Syntax error!: duplicate key "+repr(currKey)+" ;_;");
				configDict[currKey] = value;
				
				_currKey = None;
				_which = _LineEnd;
			
			elif (which == _LineEnd):
				raise Exception("Syntax error!: more than two strings on one line! o,0");
			else:
				raise AssertionError();
			
			return _which, _currKey;  #python functions-in-functions can read their parent function's variables, but not write them ;-;   (so this is a general workaround :P )
		
		
		# Todo replace the continue's with pass's after making a Unit Testing corpus :>
		
		for i in xrange(len(source)):
			c = source[i];
			
			#print("DEBUGPARSER) "+repr(i)+" : "+repr(c)+"   which="+repr(which)+", where="+repr(where)+", currKey="+repr(currKey));
			
			if (where == _BeforeString):
				if (c == "\""):
					if (which == _LineEnd):
						raise Exception("Syntax error!: more than two strings on one line!  o,0");
					start = i+1; #skip the quote ;3
					where = _InQuotedString;
				elif (c.isspace() and c != "\n" and c != "\n"):
					continue;
				elif (c == "#"):
					if (which == _Value):
						raise Exception("Syntax error!: Comment started between key and value! (which would gobble up any value!)  D:");
					where = _InComment;
				elif (c == "\n" or c == "\r"):
					if (which == _Key):
						continue; #empty line :3
					elif (which == _Value):
						which, currKey = consumestr("", False)
						continue;
					elif (which == _LineEnd):
						which = _Key;
						continue; #properly full line :3
					else:
						raise AssertionError();
				else:
					if (which == _LineEnd):
						raise Exception("Syntax error!: more than two strings on one line!  o,0");
					start = i; #don't skip the first char here! it's not a quote, it's actually part of the string! XD
					where = _InNonquotedString;
			
			elif (where == _InComment):
				if (c == "\r" or c == "\n"):
					where = _BeforeString;
					
					if (which == _Key):
						continue; #just-comment line :3
					elif (which == _Value):
						raise AssertionError(); #it should have triggered a syntax error before this! :[
					elif (which == _LineEnd):
						#properly full line with comment after it :3
						which = _Key;
						continue;
					else:
						raise AssertionError();
				else:
					continue;
			
			elif (where == _InNonquotedString):
				if (c.isspace() and c != "\n" and c != "\n"):
					# end of nonquoted string! ^w^
					if (start == None): raise AssertionError();
					if (which != _Key and which != _Value): raise AssertionError();
					which, currKey = consumestr(source[start:i], False);  #do NOT include the last char, it's the space delimiter!  (don't forget that XD' )
					start = None; #for bugchecking ^,^
					where = _BeforeString;
				
				elif (c == "\n" or c == "\r"):
					# end of nonquoted string AND line! ^^?
					if (which == _Key):
						raise Exception("Syntax error?: Line break between key and value!  D:");
					elif (which == _Value):
						# normal full line with nonquoted value :>
						which, currKey = consumestr(source[start:i], False);  #DON'T include the last char--the newline! XD'
						start = None; #for bugchecking ^,^
						which = _Key; #jump straight to start state for next line! ^w^
						where = _BeforeString;
					elif (which == _LineEnd):
						raise AssertionError();
					else:
						raise AssertionError();
				elif (c == "#"):
					if (which == _Value):
						raise Exception("Syntax error!: Comment started between key and value! (which would gobble up any value!)  D:");
					where = _InComment;
				else:
					continue;  # :3
			
			elif (where == _InQuotedString):
				if (c == "\""):
					# end of yesquoted string! ^w^
					if (start == None): raise AssertionError();
					if (which != _Key and which != _Value): raise AssertionError();
					which, currKey = consumestr(source[start:i], True);  #DON'T include the last char, it is a quote!
					start = None; #for bugchecking ^,^
					where = _BeforeString;
				elif (c == "\\"):
					where = _InQuotedString_InEscape;  # :3
				elif (c == "\n" or c == "\r"):
					#engine behavior is to act like a proper closing quote was there :>
					
					# end of yesquoted string! ^w^
					if (start == None): raise AssertionError();
					if (which != _Key and which != _Value): raise AssertionError();
					which, currKey = consumestr(source[start:i], True);  #DON'T include the last char--the newline! XD'
					start = None; #for bugchecking ^,^
					where = _BeforeString;
				else:
					continue;  # :3
			
			elif (where == _InQuotedString_InEscape):
				if (c == "\n" or c == "\r"):
					#engine behavior is to act like it wasn't there, and also that a proper closing quote was there :>
					
					# end of yesquoted string! ^w^
					if (start == None): raise AssertionError();
					if (which != _Key and which != _Value): raise AssertionError();
					which, currKey = consumestr(source[start:i], True);  #DON'T include the last char, it is that bad trailing backslash!
					start = None; #for bugchecking ^,^
					where = _BeforeString;
				
				else:
					# Note: we descape in a separate step rather than on-the-fly for simplicity+speeds ^_^   (rather than build up an eagerly descaped string char by char, which is slow if no escapes :p, and rather than a hybrid of the two approaches..which is complicated (and this is already complicated enough!) XD' )
					where = _InQuotedString;
			
			else:
				raise AssertionError();
		#
		
		
		
		# EOF inside quoted string is fine with lc2e (string is consumed just like end-of-line :> )
		# EOF on escape inside quoted string makes the escape ignored, and the string consumed by lc2e
		# EOF on nonquoted string is fine with lc2e :>
		# EOF on comment is fine; no effect different than linebreak :>
		
		if (where == _BeforeString):
			# Normal EOF; no problems! ^w^
			pass;
		elif (where == _InComment):
			pass;
		elif (where == _InNonquotedString):
			# end of nonquoted string! ^w^
			if (start == None): raise AssertionError();
			if (which != _Key and which != _Value): raise AssertionError();
			consumestr(source[start:len(source)], False);  #do include the last char like normal, since it's a nonquoted! ^w^
		elif (where == _InQuotedString):
			if (start == None): raise AssertionError();
			if (which != _Key and which != _Value): raise AssertionError();
			consumestr(source[start:len(source)], True);  #DO include the last char, it is a broken quoted string! XD'
		elif (where == _InQuotedString_InEscape):
			if (start == None): raise AssertionError();
			if (which != _Key and which != _Value): raise AssertionError();
			consumestr(source[start:len(source)-1], True);  #DON'T include the last char--the (imo erroneous :P) trailing backslash!
		else:
			raise AssertionError();
		
		
		return configDict;
		
	except AssertionError, exc:
		exc.message = "Pleases to let the puppy of codes know about this! (puppyofcodez@gmail.com)  I'll fix it right away ;_;  (just be sures to send the *exact* input config file source text!: "+repr(source)+" )   MANY SORRIES T_T";
		raise;
#




def serializeCreaturesConfig(configDict):
	# Serializing is almost *always* easier than parsing XD    (probably largely because there are so many more possible states you can start with in parsing, and that much more situations to have to handle!   but I think there's more to it than that -,-   (wonderful things to explore!! 8> )  )
	
	def containsspecials(s):
		if (len(s) == 0):
			return True;  #should be quoted if this somehow is used! XD'?
		
		if ("\"" in s or "#" in s or "\\" in s or " " in s or "\n" in s or "\r" in s or "\t" in s):  #prolly fasters than doing it in the loop!
			return True;
		
		# check other whitespace just to make sures :>
		for c in s:
			if (c.isspace()):
				return True;
		
		return False;
	
	def escapestr(s):
		s = s.replace("\\", "\\\\");
		s = s.replace("\"", "\\\"");
		s = s.replace("\n", "\\n");
		s = s.replace("\r", "\\r");
		s = s.replace("\t", "\\t");
		return s;
	
	def serstr(s):
		if (containsspecials(s)):
			return "\""+escapestr(s)+"\"";
		else:
			return s;
	
	
	serializedForm = "";
	
	for key in sorted(configDict.keys()):
		value = configDict.get(key);
		if (value != None):  #not-present OR actually-None!  ..don't forget that :>' XD'
			serializedForm += serstr(key);
			serializedForm += " ";
			serializedForm += serstr(value);
			serializedForm += "\n";
	
	return serializedForm;
#


# Dynamic CAOS-writing helper functions! :D
def caosEscape(s):
	s = s.replace("\\", "\\\\");
	s = s.replace("\"", "\\\"");
	s = s.replace("\n", "\\n");
	s = s.replace("\r", "\\r");
	s = s.replace("\t", "\\t");
	return s;

# Todo: def caosDescape(s)


def toCAOSString(s):
	return "\""+caosEscape(s)+"\"";


def toCAOSByteArray(b):
	# Heavily checked ^^", so you doesn't have to worry about using the wrong type of input and it invisibly breaking somewhere in caos construction! XD''
	if (isinstance(b, bytearray)):
		return "["+(" ".join(map(repr, b)))+"]";
	elif (isinstance(b, str)):
		return "["+(" ".join(map(lambda c: repr(ord(c)), b)))+"]";
	elif (isinstance(b, collections.Iterable)):
		if (isany(lambda v: v < 0 or v > 255, b)): raise Exception("At least one of the bytes was outside the range [0, 255], which is the range an (unsigned) byte can take! D:");
		if (isany(lambda v: not (isinstance(v, int) or isinstance(v, long)), b)): raise TypeError("Argument must be a python bytearray, iterable of *integers*, or str, sorries ;;");
		return "["+(" ".join(map(repr, b)))+"]";
	else:
		raise TypeError("Argument must be a python bytearray, iterable of integers, or str, sorries ;;");








def transientLC2EDefaultMain(args):
	"This functions as a useable function for simple applications, and also an example for others! :D"
	
	def b(session):
		session.waitForEngineToTerminate();
	#
	
	transientLC2EDefaultCoreMain(args, b)
#



def transientLC2EDefaultCoreMain(args, body):
	"This functions as a useable function for simple applications, and also an example for others! :D"
	
	def printHelp():
		print("Usage: "+os.path.basename(sys.argv[0])+" [(rwdata-instance-dir) [(rodata-pack-dir)]]");
	
	# Printing help! :D
	if (len(args) == 0 or "-h" in args or "--help" in args):
		printHelp()
		return 0
	
	try:
		config = loadDefaultConfig()
	except ConfigLoadingException, e:
		print("Error loading config!: "+e.message)
		return 8
	
	
	
	if (len(args) == 0):
		rwdataInstanceDir = Default;
		rodataPackDir = Default;
	elif (len(args) == 1):
		rwdataInstanceDir = args[0];
		rodataPackDir = None;
	elif (len(args) == 2):
		rwdataInstanceDir = args[0];
		rodataPackDir = args[1];
	else:
		printHelp()
		return 1;
	
	
	
	if (rwdataInstanceDir == Default):
		rwdataInstanceDir = "default";
	if (rodataPackDir == Default):
		rodataPackDir = "default";
	
	
	rwdataInstanceDir = os.path.join(config.rwDataInstancesSuperDirectory, rwdataInstanceDir) if not "/" in rwdataInstanceDir else os.path.abspath(rwdataInstanceDir);
	if (rodataPackDir != None): rodataPackDir = os.path.join(config.roDataPacksSuperDirectory, rodataPackDir) if not "/" in rodataPackDir else os.path.abspath(rodataPackDir);
	
	
	
	
	
	session = TransientLC2ESession(config.roEngineTemplateDataDirectory);
	
	# Be very wordy :3
	session.setLogToVerbose();
	
	session.loadDefaultsFromConfig(config)
	
	session.loadCreaturesFilesystemIntoMachineConfigAsThePrimaryReadwriteFilesystem(CreaturesFilesystem(rwdataInstanceDir));
	if (rodataPackDir != None): session.loadCreaturesFilesystemIntoMachineConfigAsTheAuxiliaryReadonlyFilesystem(CreaturesFilesystem(rodataPackDir));
	
	configureTransientLC2ESessionForStandardDockingStation(session);
	
	# Sometimes needed!?
	session.getMachineConfig()["Bootstrap Directory"] = session.getMachineConfig()["Auxiliary 1 Bootstrap Directory"];
	#session.getMachineConfig()["Auxiliary 2 Images Directory"] = session.getMachineConfig()["Auxiliary 1 Images Directory"];
	
	session.start(None, False);
	
	
	session.waitForEngineToBecomeCaosable();
	print("CAOS Test! :D     Gnam: "+session.runcaos("outs gnam"));
	print("CAOS Test! :D     Square of 9: "+session.runcaos("setv va00 9  mulv va00 va00  outv va00"));
	
	
	body(session)
	
	
	session.cleanUp();
	
	
	if (session.didEngineCrash()):
		print("It crashed! D:!!");
	else:
		print("Iiiit'ssss donnneeeeeeee! :>");
	
	return 0
#











#### Utilities! :D ####

def readallText(f, sanityLimit=16777216):
	if (getsize(f, derefSymlinks=True) > sanityLimit):
		raise Exception("File "+f+" is larger than sanityLimit "+repr(sanityLimit)+" :O");
	
	p = open(f, "rU");
	
	try:
		c = p.read(sanityLimit);
	finally:
		p.close();
	
	return c;
#


def writeallText(f, content, append=False, overwrite=False):
	if (not overwrite and os.path.lexists(f)):
		raise OSError("Can't overwrite: file node exists: "+f);
	else:
		p = open(f, "w" if not append else "a");
		
		try:
			if (not append):
				p.truncate(0); #be explicit!  (this step is normally done automatically in unix at least; but lets be allll the explicits! ^w^ )
			p.write(content);
		finally:
			p.close();
#


def getsize(f, derefSymlinks=True):
	"""
	find the size of the given file.
	If the file is not a file or is not accessible, 0 is returned.
	"""
	try:
		if (derefSymlinks):
			if (os.path.isfile(f)):
				return os.path.getsize(f);
			else:
				return 0;
		else:
			if (os.path.islink(f) or os.path.isfile(f)):
				return os.lstat(f).st_size;
			else:
				return 0;
	except OSError, exc:
		if (exc.errno == errno.EACCES): # Permission denied
			return 0;
		elif (exc.errno == errno.ENOENT): # File not found
			return 0;
		else:
			raise;
#




_GlobalGCListeners = set();

def registerGCListener(referent, nullaryCallback):
	# "If callback is provided and not None, and the returned weakref object is still alive, the callback will be called when the object is about to be finalized"...
	# So python, like Java, *almost* provides garbage-collection listeners XD'
	# We just need to make sure the weak reference objects stay alive (which is kind of arbitrary; in a real GC-listener system like I made up (XD'), it wouldn't even require that :> )
	
	def gclistener(theweakref):
		_GlobalGCListeners.remove(theweakref);  #how nice of them to provide it to us! :D
		nullaryCallback();
	
	#note: because we're currently holding a (strong) reference to the referent, the GC listener won't be called between when (after) the weakref.ref() is created but before it's added to the global listeners set!  ^_^
	r = weakref.ref(referent)
	
	_GlobalGCListeners.add(r);
#





def isany(predicate, iterable):
	for x in iterable:
		if (predicate(x)):
			return True;
	return False;


def isall(predicate, iterable):
	for x in iterable:
		if (not predicate(x)):
			return False;
	return True;



# Necessary hook-thing in python codes to make it both an importable library module, *and* an executable program in its own right! :D    (like C and Java come with by default :P   which has pros and cons :> )
if (__name__ == "__main__"):
	sys.exit(transientLC2EDefaultMain(sys.argv[1:]));
