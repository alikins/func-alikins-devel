#!/usr/bin/python

## func
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
##

import codes
from modules import func_module

import sub_process
import os

class Service(func_module.FuncModule):

    def __init__(self):
        self.methods = {
            "start"       : self.start,
            "stop"        : self.stop,
            "restart"     : self.restart,
            "reload"      : self.reload,
            "status"      : self.status,
            "get_enabled" : self.get_enabled,
            "get_running" : self.get_running,
            "inventory"   : self.inventory,
        }
        func_module.FuncModule.__init__(self)

    def __command(self, service_name, command):

        filename = os.path.join("/etc/rc.d/init.d/",service_name)
        if os.path.exists(filename):
            return sub_process.call(["/sbin/service", service_name, command])
        else:
            raise codes.FuncException("Service not installed: %s" % service_name)

    def start(self, service_name):
        return self.__command(service_name, "start")

    def stop(self, service_name):
        return self.__command(service_name, "stop")

    def restart(self, service_name):
        return self.__command(service_name, "restart")

    def reload(self, service_name):
        return self.__command(service_name, "reload")

    def status(self, service_name):
        return self.__command(service_name, "status")

    def inventory(self):
        return {
            "running" : self.get_running(),
            "enabled" : self.get_enabled()
        }

    def get_enabled(self):
        chkconfig = sub_process.Popen(["/sbin/chkconfig", "--list"], stdout=sub_process.PIPE)
        data = chkconfig.communicate()[0]
        results = []
        for line in data.split("\n"):
            if line.find("0:") != -1:
               # regular services
               tokens = line.split()
               results.append((tokens[0],tokens[1:]))
            elif line.find(":") != -1 and not line.endswith(":"):
               # xinetd.d based services
               tokens = line.split()
               tokens[0] = tokens[0].replace(":","")
               results.append((tokens[0],tokens[1]))
        return results

    def get_running(self):
        return {

        }

methods = Service()
register_rpc = methods.register_rpc
