"""
Virt management features

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

# warning: virt management is rather complicated
# to see a simple example of func, look at the
# service control module.  API docs on how
# to use this to come.

# xml modules
import StringIO
from xml.dom import minidom

# other modules
import os
import sub_process
import libvirt

# our modules
import codes
import func_module

VIRT_STATE_NAME_MAP = {
   0 : "running",
   1 : "running",
   2 : "running",
   3 : "paused",
   4 : "shutdown",
   5 : "shutdown",
   6 : "crashed"
}

class FuncLibvirtConnection(object):

    version = "0.0.1"
    api_version = "0.0.1"
    description = "Virtualization items through func."

    def __init__(self):

        cmd = sub_process.Popen("uname -r", shell=True, stdout=sub_process.PIPE,
                                close_fds=True)
        output = cmd.communicate()[0]

        if output.find("xen") != -1:
            conn = libvirt.open(None)
        else:
            conn = libvirt.open("qemu:///system")

        if not conn:
            raise codes.FuncException("hypervisor connection failure")

        self.conn = conn

    def find_vm(self, vmid):
        """
        Extra bonus feature: vmid = -1 returns a list of everything
        """
        conn = self.conn

        vms = []

        # this block of code borrowed from virt-manager:
        # get working domain's name
        ids = conn.listDomainsID();
        for id in ids:
            vm = conn.lookupByID(id)
            vms.append(vm)
        # get defined domain
        names = conn.listDefinedDomains()
        for name in names:
            vm = conn.lookupByName(name)
            vms.append(vm)

        if vmid == -1:
            return vms

        for vm in vms:
            if vm.name() == vmid:
                return vm

        raise codes.FuncException("virtual machine %s not found" % vmid)

    def shutdown(self, vmid):
        return self.find_vm(vmid).shutdown()

    def pause(self, vmid):
        return self.suspend(self.conn,vmid)

    def unpause(self, vmid):
        return self.resume(self.conn,vmid)

    def suspend(self, vmid):
        return self.find_vm(vmid).suspend()

    def resume(self, vmid):
        return self.find_vm(vmid).resume()

    def create(self, vmid):
        return self.find_vm(vmid).create()

    def destroy(self, vmid):
        return self.find_vm(vmid).destroy()

    def undefine(self, vmid):
        return self.find_vm(vmid).undefine()

    def get_status2(self, vm):
        state = vm.info()[0]
        # print "DEBUG: state: %s" % state
        return VIRT_STATE_NAME_MAP.get(state,"unknown")

    def get_status(self, vmid):
        state = self.find_vm(vmid).info()[0]
        return VIRT_STATE_NAME_MAP.get(state,"unknown")

    def nodeinfo(self):
        return self.conn.getInfo()

    def get_type(self):
        return self.conn.getType()


class Virt(func_module.FuncModule):

    def __get_conn(self):
        self.conn = FuncLibvirtConnection()
        return self.conn

    def state(self):
        vms = self.list_vms()
        state = []
        for vm in vms:
            state_blurb = self.conn.get_status(vm)
            state.append("%s %s" % (vm,state_blurb))
        return state


    def info(self):
        vms = self.list_vms()
        info = dict()
        for vm in vms:
            data = self.conn.find_vm(vm).info()
            # libvirt returns maxMem, memory, and cpuTime as long()'s, which
            # xmlrpclib tries to convert to regular int's during serialization.
            # This throws exceptions, so convert them to strings here and
            # assume the other end of the xmlrpc connection can figure things
            # out or doesn't care.
            info[vm] = {
                "state"     : VIRT_STATE_NAME_MAP.get(data[0],"unknown"),
                "maxMem"    : str(data[1]),
                "memory"    : str(data[2]),
                "nrVirtCpu" : data[3],
                "cpuTime"   : str(data[4])
            }
        return info

    def nodeinfo(self):
        self.__get_conn()
        info = dict()
        data = self.conn.nodeinfo()
        info = {
            "cpumodel"     : str(data[0]),
            "phymemory"    : str(data[1]),
            "cpus"         : str(data[2]),
            "cpumhz"       : str(data[3]),
            "numanodes"    : str(data[4]),
            "sockets"      : str(data[5]),
            "cpucores"     : str(data[6]),
            "cputhreads"   : str(data[7])
        }
        return info

    def list_vms(self):
        self.conn = self.__get_conn()
        vms = self.conn.find_vm(-1)
        results = []
        for x in vms:
            try:
                results.append(x.name())
            except:
                pass
        return results

    def virttype(self):
	return self.__get_conn().get_type()

    def autostart(self, vm):
	self.conn = self.__get_conn()
	if self.conn.get_type() == "Xen":
	    autostart_args = [
		"/bin/ln",
		"-s",
		"/etc/xen/%s" % vm,
		"/etc/xen/auto"
	    ]
        else:
            # When using KVM, we need to make sure the autostart
            # directory exists
	    mkdir_args = [
		"/bin/mkdir",
		"-p",
		"/etc/libvirt/qemu/autostart"
	    ]
            sub_process.call(mkdir_args,shell=False,close_fds=True)

            # We aren't using virsh autostart because we want
            # the command to work even when the VM isn't running
	    autostart_args = [
		"/bin/ln",
		"-s",
		"/etc/libvirt/qemu/%s.xml" % vm,
		"/etc/libvirt/qemu/autostart/%s.xml" % vm
	    ]

        return sub_process.call(autostart_args,shell=False,close_fds=True)

    def freemem(self):
        self.conn = self.__get_conn()
        # Start with the physical memory and subtract
        memory = self.conn.nodeinfo()[1]

        # Take 256M off which is reserved for Domain-0
        memory = memory - 256

        vms = self.conn.find_vm(-1)
        for vm in vms:
            # Exclude stopped vms and Domain-0 by using
            # ids greater than 0
            if vm.ID() > 0:
                # This node is active - remove its memory (in bytes)
                memory = memory - int(vm.info()[2])/1024

        return memory

    def install(self, server_name, target_name, system=False, virt_name=None, virt_path=None, graphics=False):

        """
        Install a new virt system by way of a named cobbler profile.
        """

        # Example:
        # install("bootserver.example.org", "fc7webserver", True)
        # install("bootserver.example.org", "client.example.org", True, "client-disk0", "HostVolGroup00")

        conn = self.__get_conn()

        if conn is None:
            raise codes.FuncException("no connection")

        if not os.path.exists("/usr/bin/koan"):
            raise codes.FuncException("no /usr/bin/koan")
        target = "profile"
        if system:
            target = "system"

        koan_args = [
            "/usr/bin/koan",
            "--virt",
            "--%s=%s" % (target, target_name),
            "--server=%s" % server_name
        ]

        if virt_name:
            koan_args.append("--virt-name=%s" % virt_name)

        if virt_path:
            koan_args.append("--virt-path=%s" % virt_path)

        if not graphics:
            koan_args.append("--nogfx")

        rc = sub_process.call(koan_args,shell=False,close_fds=True)
        if rc == 0:
            return 0
        else:
            raise codes.FuncException("koan returned %d" % rc)


    def shutdown(self, vmid):
        """
        Make the machine with the given vmid stop running.
        Whatever that takes.
        """
        self.__get_conn()
        self.conn.shutdown(vmid)
        return 0


    def pause(self, vmid):

        """
        Pause the machine with the given vmid.
        """
        self.__get_conn()
        self.conn.suspend(vmid)
        return 0


    def unpause(self, vmid):

        """
        Unpause the machine with the given vmid.
        """

        self.__get_conn()
        self.conn.resume(vmid)
        return 0


    def create(self, vmid):

        """
        Start the machine via the given mac address.
        """
        self.__get_conn()
        self.conn.create(vmid)
        return 0


    def destroy(self, vmid):

        """
        Pull the virtual power from the virtual domain, giving it virtually no
        time to virtually shut down.
        """
        self.__get_conn()
        self.conn.destroy(vmid)
        return 0


    def undefine(self, vmid):

        """
        Stop a domain, and then wipe it from the face of the earth.
        by deleting the disk image and it's configuration file.
        """

        self.__get_conn()
        self.conn.undefine(vmid)
        return 0


    def get_status(self, vmid):

        """
        Return a state suitable for server consumption.  Aka, codes.py values, not XM output.
        """

        self.__get_conn()
        return self.conn.get_status(vmid)


    def get_xml(self, vmid):
        """
	Recieve a Vm id as input
        Return an xml describing vm config returned by a libvirt call
	"""
	conn = libvirt.openReadOnly(None)
	if conn == None:
		return (-1,'Failed to open connection to the hypervisor')
	try:
		domV = conn.lookupByName(vmid)
	except:
		return (-1,'Failed to find the main domain')
	return domV.XMLDesc(0)


    def get_graphics(self,vmid,xml='None'):
	"""
	Recieve a Vm id as input
	Read machine informations from xml config,
	return a key/val map containing only graphics properties
	"""
	out = {'autoport': 'None', 'keymap': 'None', 'type': 'vnc', 'port': 'None', 'listen': 'None'}
	if(xml=='None'):
	    xml = self.get_xml(vmid)
	else:
	    xml = "<domain>\n"+xml+"\n</domain>"
	ssock = StringIO.StringIO(xml)
	doc = minidom.parse(ssock)
	for node in doc.getElementsByTagName("domain"):
	    graphics = node.getAttribute("devices")
	    L = node.getElementsByTagName("graphics")
	    for node2 in L:
		for k in node2.attributes.keys():
		    out[k] = node2.getAttribute(k)
	return out


    def set_graphics(self,vmid,xml):
	"""
	Recieve a Vm id and a piece of xml as input
	Set vnc address and parameters of vm in xml config file
	Return 0 if config has been correctly written
	"""
	try:
	   conn = libvirt.openReadOnly(None)
	   tmp = conn.getType()
	except:
	   return (-1,'Failed to open connection to the hypervisor')
	strxml = self.get_graphics(vmid,xml)
	str = "vfb = [ \"vncunused=1, "

	for el in strxml:
	    if(strxml[el] != 'None'):
		if(el == 'port'):
		    str = "%s%s=\'%s\', " % (str,"vncdisplay",(int(strxml[el])-5900))
		else:
		    str = "%s%s=\'%s\', " % (str,el,strxml[el])
	str = "%s\" ]" % str.rstrip(' ').rstrip(',')

	if(tmp == "Xen"):
	    if os.path.exists("/etc/xen/%s" % vmid):
		return os.system("sed -i 's/^vfb.*/%s/g' /etc/xen/%s" % (str,vmid))
	    else:
		return (-1,'Config file /etc/xen/%s not found' % vmid)
	else:
	    if os.path.exists("/etc/libvirt/qemu/%s.xml" % vmid):
		xml = self.get_xml(vmid)
		ssock = StringIO.StringIO(xml)
		doc = minidom.parse(ssock)
		for node in doc.getElementsByTagName("domain"):
		    graphics = node.getAttribute("devices")
		    L = node.getElementsByTagName("graphics")
		    for node2 in L:
			for el in strxml:
                            if(strxml[el] != 'None'):
                                node2.setAttribute(el,strxml[el])
		output_xml = open("/etc/libvirt/qemu/%s.xml" % vmid, 'w')
		output_xml.write(node.toxml())
		return 0
	    else:
		return (-1,'Config file /etc/libvirt/qemu/%s.xml not found' % vmid)
	return (-2,'Unmatched Condition in set_graphics method')

