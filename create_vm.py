import requests
import json
from typing import Dict, Any

# vCSA connection settings
VCSA_URL = "https://10.10.203.119"
USERNAME = "administrator@vsphere.local"
PASSWORD = "QAZ123wsx!@#"

# VM configuration
VM_NAME = "New_VM2"
CPU_COUNT = 2
MEMORY_SIZE_MB = 1024
DISK_SIZE_GB = 5
DATASTORE = "datastore1"
NETWORK_NAME = "VM Network"
GUEST_OS = 'OTHER_LINUX_64'  # This is the correct format for vCSA 8

# Disable SSL warnings
requests.packages.urllib3.disable_warnings()

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
        client = VCSAClient(VCSA_URL, USERNAME, PASSWORD)
        
        # Get required resources
        resource_pool = client.get_resource_pool()
        datastore = client.get_datastore(DATASTORE)
        network = client.get_network(NETWORK_NAME)
        folder = client.get_folder()

        # Prepare VM specification
        vm_spec = {
            "spec": {
                "name": VM_NAME,
                "guest_OS": GUEST_OS,
                "placement": {
                    "resource_pool": resource_pool,
                    "datastore": datastore,
                    "folder": folder
                },
                "hardware": {
                    "cpu": {"count": CPU_COUNT},
                    "memory": {"size_MiB": MEMORY_SIZE_MB},
                    "disks": [{
                        "new_vmdk": {
                            "capacity": DISK_SIZE_GB * 1024 * 1024 * 1024
                        },
                        "type": "VIRTUAL_DISK"
                    }],
                    "nics": [{
                        "backing": {
                            "type": "STANDARD_PORTGROUP",
                            "network": network
                        },
                        "start_connected": True,
                        "type": "VMXNET3"
                    }]
                }
            }
        }

        # Create VM
        result = client.create_vm(vm_spec)
        print(f"VM created successfully: {result}")

    except requests.exceptions.RequestException as e:
        print(f"Network error occurred: {e}")
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
