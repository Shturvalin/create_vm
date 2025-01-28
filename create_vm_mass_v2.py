import requests
import json
from typing import Dict, Any

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

# vCSA connection settings
VCSA_URL = "https://10.10.203.119"
USERNAME = "administrator@vsphere.local"
PASSWORD = "QAZ123wsx!@#"

# Network and storage settings
DATASTORE = "datastore1"
NETWORK_NAME = "VM Network"
GUEST_OS = 'DOS'  # Changed to MS-DOS

def get_vm_config():
    print("\nEnter VM configuration:")
    cpu_count = int(input("Number of CPU cores: "))
    memory_size = int(input("Memory size in MB: "))  # Direct MB input
    disk_size_mb = int(input("Disk size in MB: "))
    return cpu_count, memory_size, disk_size_mb

def get_vm_names():
    print("\nEnter VM names (space-separated):")
    names = input().split()
    return names

class VCSAClient:
    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.username = username
        self.password = password
        self.session_id = self._get_session_id()
        self.headers = {'vmware-api-session-id': self.session_id}

    def _get_session_id(self) -> str:
        url = f"{self.url}/rest/com/vmware/cis/session"
        response = requests.post(url, auth=(self.username, self.password), verify=False)
        response.raise_for_status()
        return response.json()['value']

    def get_resource_pool(self) -> str:
        url = f"{self.url}/rest/vcenter/resource-pool"
        response = requests.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        resource_pools = response.json()['value']
        if not resource_pools:
            raise ValueError("No resource pool found")
        return resource_pools[0]['resource_pool']

    def get_datastore(self, datastore_name: str) -> str:
        url = f"{self.url}/rest/vcenter/datastore"
        response = requests.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        datastores = response.json()['value']
        for datastore in datastores:
            if datastore['name'] == datastore_name:
                return datastore['datastore']
        raise ValueError(f"Datastore '{datastore_name}' not found")

    def get_network(self, network_name: str) -> str:
        url = f"{self.url}/rest/vcenter/network"
        response = requests.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        networks = response.json()['value']
        for network in networks:
            if network['name'] == network_name:
                return network['network']
        raise ValueError(f"Network '{network_name}' not found")

    def get_folder(self) -> str:
        url = f"{self.url}/rest/vcenter/folder"
        response = requests.get(url, headers=self.headers, verify=False)
        response.raise_for_status()
        folders = response.json()['value']
        vm_folders = [f for f in folders if f['type'] == 'VIRTUAL_MACHINE']
        if not vm_folders:
            raise ValueError("No VM folder found")
        return vm_folders[0]['folder']

    def create_vm(self, vm_spec: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.url}/rest/vcenter/vm"
        headers = {**self.headers, 'Content-Type': 'application/json'}
        response = requests.post(url, headers=headers, json=vm_spec, verify=False)
        
        if response.status_code == 400:
            error_msg = response.json()
            raise ValueError(f"VM creation failed: {error_msg}")
            
        response.raise_for_status()
        return response.json()

def main():
    try:
        cpu_count, memory_size, disk_size_mb = get_vm_config()
        vm_names = get_vm_names()
        
        client = VCSAClient(VCSA_URL, USERNAME, PASSWORD)
        
        resource_pool = client.get_resource_pool()
        datastore = client.get_datastore(DATASTORE)
        network = client.get_network(NETWORK_NAME)
        folder = client.get_folder()

        for vm_name in vm_names:
            vm_spec = {
                "spec": {
                    "name": vm_name,
                    "guest_OS": GUEST_OS,
                    "placement": {
                        "resource_pool": resource_pool,
                        "datastore": datastore,
                        "folder": folder
                    },
                    "memory": {
                        "size_MiB": memory_size
                    },
                    "cpu": {
                        "count": cpu_count
                    },
                    "disks": [
                        {
                            "new_vmdk": {
                                "name": f"{vm_name}_disk1",
                                "capacity": disk_size_mb * 1024 * 1024
                            }
                        }
                    ],
                    "nics": [
                        {
                            "backing": {
                                "type": "STANDARD_PORTGROUP",
                                "network": network
                            }
                        }
                    ]
                }
            }
            
            result = client.create_vm(vm_spec)
            print(f"VM {vm_name} created successfully with {cpu_count} CPUs, {memory_size}MB RAM, and {disk_size_mb}MB disk: {result}")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {e}")
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
