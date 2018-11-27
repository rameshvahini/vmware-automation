import requests
import sys
import re
from passwd import user_api, pass_api
from python_terraform import *
import atexit
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim
from tools import tasks
from tools import tasks
from tools import cli


# get ip address
def ipam_create_ip(hostname, infraname, cidr):
    token = requests.post('https://ipam.phoenixit.ru/api/apiclient/user/', auth=(user_api, pass_api)).json()['data']['token']
    headers = {'token':token}
    cidr_url = 'http://ipam.phoenixit.ru/api/apiclient/subnets/cidr/' + cidr
    get_sudnet_id = requests.get(url=cidr_url, headers=headers).json()['data'][0]['id']
    get_ip_url = "https://ipam.phoenixit.ru/api/apiclient/addresses/first_free/"+get_sudnet_id
    ip = requests.get(url=get_ip_url, headers=headers).json()['data']
    create_url = "https://ipam.phoenixit.ru/api/apiclient/addresses/?subnetId="+get_sudnet_id+"&ip="+ip+"&hostname="+hostname+"&description="+infraname
    create = requests.post(url = create_url , headers=headers).json()['success']
    if create == True:
        return ip  # get ip address


#folder project terraform (linux&windows) return ter_dir (./linux, ./windows)
def template(vm_template):
    template_linux = ['template_centos7.3', 'template_ubuntu16.04']
    template_wind = ['template_wind2012', 'template_wind2008']
    if vm_template in template_linux:
        ter_dir = './linux'
        return ter_dir
    elif vm_template in template_wind:
        ter_dir = './windows'
        return ter_dir
    else:
        print ('no template')



#varible
def create_vm_terraform(ter_dir, hostname, ip, cidr, vc_host, vc_user, vc_pass, vc_dc, vc_cluster, vc_storage, vm_template,
                        vm_cpu, vm_ram, vm_disk_size ):
    vm_ip_gw = re.sub('[/]', '', cidr)[:-3] + '1'  # get GW (example 192.168.222.1)
    vm_netmask = cidr[-2:]   # get prefix netmask (example /24)вд
#get port_group_vm_interface  (return portgroup)
    def portgroup(cidr):
        port_int = {'192.168.222.0/24': '192.168.222',
                    '192.168.199.0/24': '192.168.199',
                    '192.168.245.0/24': '245'}

        if port_int[cidr]:
            vm_portgroup = port_int.get(cidr)
            return vm_portgroup
        else:
            print ('no network portgroup')



    vm_portgroup = portgroup(cidr)
    tf = Terraform(working_dir=ter_dir, variables={'vc_host': vc_host,
                                                   'vc_user': vc_user, 'vc_pass': vc_pass,
                                                   'vc_dc': vc_dc, 'vc_cluster': vc_cluster, 'vc_storage': vc_storage,
                                                   'vm_portgroup': vm_portgroup, 'vm_template': vm_template,
                                                   'vm_hostname': hostname, 'vm_cpu': vm_cpu, 'vm_ram': vm_ram,
                                                   'vm_disk_size': vm_disk_size, 'vm_ip': ip, 'vm_ip_gw': vm_ip_gw,
                                                   'vm_netmask': vm_netmask})
    kwargs = {"auto-approve": True}
    print(kwargs)
    tf.init()
    print(tf.plan())
    print(tf.apply(**kwargs))


#change folder, write notes

def notes_write_vm(vc_host, vc_user, vc_pass, ip, infraname):
    service_instance = connect.SmartConnectNoSSL(host=vc_host,
                                                    user=vc_user,
                                                     pwd=vc_pass,
                                                     port=443)
    config_uuid = service_instance.content.searchIndex.FindByIp(None, ip, True)
    uuid = config_uuid.summary.config.instanceUuid
    message = ip + " " + infraname
    vm = service_instance.content.searchIndex.FindByUuid(None, uuid, True, True)
    print("Found: {0}".format(vm.name))
    spec = vim.vm.ConfigSpec()
    spec.annotation = message
    task = vm.ReconfigVM_Task(spec)


def move_vm_to_folder(vc_host, vc_user, vc_pass, ip, folder_vm):
    folder_dc = { 'vc-linx.srv.local': 'Datacenter-Linx/vm/',
                  'vcsa.srv.local'  : 'Datacenter-AKB/vm/',
                  'vc-khut.srv.local': 'Datacenter-KHUT/vm/'}.get(vc_host)
    service_instance = connect.SmartConnectNoSSL(host=vc_host,
                                                    user=vc_user,
                                                     pwd=vc_pass,
                                                     port=443)
    config_uuid = service_instance.content.searchIndex.FindByIp(None, ip, True)
    uuid = config_uuid.summary.config.instanceUuid
    vm = service_instance.content.searchIndex.FindByUuid(None, uuid, True, True)
    spec = vim.vm.ConfigSpec()
    task = vm.ReconfigVM_Task(spec)
    tasks.wait_for_tasks(service_instance, [task])
    folder = service_instance.content.searchIndex.FindByInventoryPath(folder_dc+folder_vm)
    print(folder)
    folder.MoveIntoFolder_Task([config_uuid])




def main(hostname, infraname, cidr, vc_host, vc_user, vc_pass, vc_dc, vc_cluster, vc_storage, vm_template,
         vm_cpu, vm_ram, vm_disk_size, folder_vm):
    ip = ipam_create_ip(hostname, infraname, cidr)
    ter_dir = template(vm_template)
    create_vm_terraform(ter_dir, hostname, ip, cidr, vc_host, vc_user, vc_pass, vc_dc, vc_cluster, vc_storage, vm_template,
                        vm_cpu, vm_ram, vm_disk_size)
    notes_write_vm(vc_host, vc_user, vc_pass, ip, infraname)
    move_vm_to_folder(vc_host, vc_user, vc_pass, ip, folder_vm)







# main (hostname='host889', infraname='INFRA8888', cidr='192.168.222.0/24', vc_host='vc-linx.srv.local',
#       vc_user='', vc_pass='', vc_dc='Datacenter-Linx', vc_cluster='linx-cluster01',
# vc_storage='27_localstore_r10', vm_template='template_centos7.3', vm_cpu='1', vm_ram='2048', vm_disk_size='30',
#       folder_vm = 'test')




