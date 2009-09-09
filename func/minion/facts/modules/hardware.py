import fact_module
import sys
import traceback

class HardwareFacts(fact_module.BaseFactModule):
    """
    Will give some basic info abouut hardware things
    """
    version = "0.0.1"
    description = "A modules that supplies hardware facts"

    def __init__(self):
        super(HardwareFacts,self).__init__()
        try:
            sys.path.append("/usr/share/smolt/client")
            import smolt
        except ImportError, e:
            errmsg = "Import error while loading smolt for the hardware facts module. Smolt is probably not installed. This module is useless without it."
            self.logger.warning(errmsg)
            self.logger.warning("%s" % traceback.format_exc())
            # hmm, what to return... 
            return 

        hardware = smolt.Hardware()
        self.host = hardware.host

    def run_level(self):
        """
        The runlevel of the system
        """
        return str(self.host.defaultRunlevel)

    #for easier acces be creful should be unique
    run_level.tag = "runlevel"

    def os_name(self):
        """
        Gives back the os name of the system
        """
        return str(self.host.os)
    
    #for easier acces be creful should be unique
    os_name.tag = "os"

    
    def cpu_vendor(self):
        """
        The cpu vendor easy one
        """
        return str(self.host.cpuVendor)

    cpu_vendor.tag = "cpuvendor"

    
    def cpu_model(self):
        """
        Cpu model
        """
        return str(self.host.cpuModel)
 
    cpu_model.tag = "cpumodel"

    def kernel_version(self):
        """
        Kernel version
        """
        return str(self.host.kernelVersion)
    
    kernel_version.tag = "kernel"



