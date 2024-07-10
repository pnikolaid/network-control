import paramiko
import subprocess
from parameters import experiment_setup, hosts

def get_used_ports_via_paramiko(hostname, port, username, password):
    # Initialize the SSH client
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the remote server
        client.connect(hostname, port, username, password)

        # Execute the command to get the list of used ports
        stdin, stdout, stderr = client.exec_command('ss -tuln')

        # Read the command output
        output = stdout.read().decode('utf-8')
        
        # Parse the output to extract port numbers
        used_ports = set()
        for line in output.splitlines():
            if line.startswith('tcp') or line.startswith('udp'):
                parts = line.split()
                local_address = parts[4]
                port = local_address.split(':')[-1]
                if port.isdigit():
                    used_ports.add(int(port))
        
        return used_ports
    finally:
        # Close the SSH connection
        client.close()

def main(setup, host_dictionary):

    # Remote server details
    server = host_dictionary[setup['server'][0][0]]
    hostname = server["IP"]
    port = server["port"]
    username = server["username"]
    password = server["password"]

    # Get the used ports from the remote server
    used_ports = get_used_ports_via_paramiko(hostname, port, username, password)
    
    # Store the used ports to a file
    server_used_ports = sorted(used_ports)
    return server_used_ports

if __name__ == "__main__":
    print(main(experiment_setup, hosts))
