##
## Hardware profiler plugin
## requires the "smolt" client package be installed
## but also relies on lspci for some things
##
## Copyright 2007, Red Hat, Inc
## Michael DeHaan <mdehaan@redhat.com>
##
## This software may be freely redistributed under the terms of the GNU
## general public license.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
##


# other modules
import sys
import traceback
from gettext import gettext
_ = gettext

# our modules
import sub_process
import func_module

# =================================

class HardwareModule(func_module.FuncModule):

    version = "0.0.1"
    api_version = "0.0.1"
    description = "Hardware profiler."

    def hal_info(self):
        """
        Returns the output of lshal, but split up into seperate devices
        for easier parsing.  Each device is a entry in the return hash.
        """

        cmd = sub_process.Popen(["/usr/bin/lshal"],shell=False,stdout=sub_process.PIPE,close_fds=True)
        data = cmd.communicate()[0]

        data = data.split("\n")

        results = {}
        current = ""
        label = data[0]
        for d in data:
            if d == '':
                results[label] = current
                current = ""
                label = ""
            else:
                if label == "":
                    label = d
                current = current + d

        return results

    def inventory(self):
        data = hw_info(with_devices=True)
        # remove bogomips because it keeps changing for laptops
        # and makes inventory tracking noisy
        if data.has_key("bogomips"):
            del data["bogomips"]
        return data

    @func_module.findout
    def grep(self,word):
        """
        Find something in hardware info 
        """
        result = {self.info:[]}
        hw_info = self.info()

        if hw_info == []:
            return []

        for hw_k,hw_v in hw_info.iteritems():
            if hw_k.lower().find(word)!=-1:
                result[self.info].append({hw_k:hw_v})
            #we should see if the value is 
            elif type(hw_v)==str and hw_v.lower().find(word)!=-1:
                result[self.info].append({hw_k:hw_v})
            elif type(hw_v)==list:
                #as it si known the hw_info has a devices 
                #in its final data and it is in format of:
                #[{key:val}] so should check it also
                for device in hw_v:
                    for d_k,d_v in device.iteritems():
                        if d_k.lower().find(word)!=-1:
                            result[self.info].append({d_k:d_v})
                        elif d_v.lower().find(word)!=-1:
                            result[self.info].append({d_k:d_v})
        
        #get the final result
        return result



    def info(self,with_devices=True):
        """
        Returns a struct of hardware information.  By default, this pulls down
        all of the devices.  If you don't care about them, set with_devices to
        False.
        """

        # this will fail if smolt is not installed.  That's ok.  hal_info will
        # still work.

        # hack: smolt is not installed in site-packages
        try:
            sys.path.append("/usr/share/smolt/client")
            import smolt
        except ImportError, e:
            errmsg = _("Import error while loading smolt module. Smolt is probably not installed. This method is useless without it.")
            self.logger.warning(errmsg)
            self.logger.warning("%s" % traceback.format_exc())
            # hmm, what to return... 
            return []

        hardware = smolt.Hardware()
        host = hardware.host

        # NOTE: casting is needed because these are DBusStrings, not real strings
        data = {
            'os'              : str(host.os),
            'defaultRunlevel' : str(host.defaultRunlevel),
            'bogomips'        : str(host.bogomips),
            'cpuVendor'       : str(host.cpuVendor),
            'cpuModel'        : str(host.cpuModel),
            'numCpus'         : str(host.numCpus),
            'cpuSpeed'        : str(host.cpuSpeed),
            'systemMemory'    : str(host.systemMemory),
            'systemSwap'      : str(host.systemSwap),
            'kernelVersion'   : str(host.kernelVersion),
            'language'        : str(host.language),
            'platform'        : str(host.platform),
            'systemVendor'    : str(host.systemVendor),
            'systemModel'     : str(host.systemModel),
            'formfactor'      : str(host.formfactor),
            'selinux_enabled' : str(host.selinux_enabled),
            'selinux_enforce' : str(host.selinux_enforce)
        }

        # if no hardware info requested, just return the above bits
        if not with_devices:
            return data

        collection = data["devices"] = []

        for item in hardware.deviceIter():

            (VendorID,DeviceID,SubsysVendorID,SubsysDeviceID,Bus,Driver,Type,Description) = item

            collection.append({
                "VendorID"       : str(VendorID),
                "DeviceID"       : str(DeviceID),
                "SubsysVendorID" : str(SubsysVendorID),
                "Bus"            : str(Bus),
                "Driver"         : str(Driver),
                "Type"           : str(Type),
                "Description"    : str(Description)
            })

        return data



        def register_method_args(self):
            """
            Implementing the argument getter
            """

            return{
                    'hal_info':{
                        'args':{},
                        'description':'Returns the output of lshal'},
                    'inventory':{
                        'args':{},
                        'description':"The inventory part"
                        },
                    'info':{
                        'args':{
                            'with_devices':{
                                'type':'boolean',
                                'optional':True,
                                'default':True,
                                'description':'All devices'
                                }
                            },
                        'description':"A struct of hardware information"
                        }
                    }

    # =================================

