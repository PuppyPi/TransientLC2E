import sys, os;

_ourdir = os.path.dirname(os.path.realpath(__file__));

Transient_LC2E_TransientSessions_SuperDirectory = os.path.join(_ourdir, "running-transient-sessions");
Transient_LC2E_RWDataInstances_SuperDirectory = os.path.join(_ourdir, "rw-instances");
Transient_LC2E_RODataPacks_SuperDirectory = os.path.join(_ourdir, "ro-datapacks");
Transient_LC2E_ROEngineTemplateData_Directory = os.path.join(_ourdir, "ro-engine");
Transient_LC2E_ErrorReportPackages_Directory = os.path.join(_ourdir, "error-reports");
