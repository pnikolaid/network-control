from parameters import hosts, all_hosts, experiment_folder, bash_folder, experiment_setup
from download_QoS_files import create_ssh_client
from get_server_used_ports import get_used_ports
import time

# Establish ssh clients for all hosts
ssh_client_dic = {}
for host_name in all_hosts:
    host = all_hosts[host_name]
    print(f"Creating ssh client at {host_name}")
    ssh_client = create_ssh_client(host["IP"], host["port"], host["username"], host["password"])
    ssh_client_dic[host_name] = ssh_client

# Find server ports to be used
server_name = experiment_setup['server'][0][0]
server_ssh = ssh_client_dic[server_name]

openrtist_num_ports = 0
iperf3_DL_num_ports = 0
iperf3_UL_num_ports = 0
for key in experiment_setup.keys():
    if key == 'sever':
        continue
    tuples = experiment_setup[key]
    if 'OpenRTiST' in key:
        for element in tuples:
            openrtist_num_ports += element[1]
    if 'iperf3_DL' in key:
        for element in tuples:
            iperf3_DL_num_ports += element[1]
    if 'iperf3_UL' in key:
        for element in tuples:
            iperf3_UL_num_ports += element[1]

openrtist_start_port = 9201
iperf3_DL_start_port = 5501
iperf3_UL_start_port = 5601
openrtist_ports = []
iperf3_DL_ports = []
iperf3_UL_ports = []
used_ports = get_used_ports(server_ssh)

current_port = openrtist_start_port
for e in range(openrtist_num_ports):
    while current_port in used_ports:
        current_port += 1
    openrtist_ports.append(current_port)
    used_ports.append(current_port)

current_port = iperf3_DL_start_port
for e in range(iperf3_DL_num_ports):
    while current_port in used_ports:
        current_port += 1
    iperf3_DL_ports.append(current_port)
    used_ports.append(current_port)

current_port = iperf3_UL_start_port
for e in range(iperf3_UL_num_ports):
    while current_port in used_ports:
        current_port += 1
    iperf3_UL_ports.append(current_port)
    used_ports.append(current_port)


print('OpenRTiST ports:', openrtist_ports)
print('iperf3-DL ports:', iperf3_DL_ports)
print('iperf3-UL ports:', iperf3_UL_ports)


# Stop all procedures on each host
stop_commands = [f"cd {bash_folder} \n sudo ./stop_clients.sh", f"cd {bash_folder} \n sudo ./stop_servers.sh", f"cd {bash_folder} \n sudo ./stop_5G.sh", f"cd {bash_folder} \n sudo ./stop_quectel.sh"]
for host_name in all_hosts:
    print(f'Stopping processes in host {host_name}')
    ssh_client = ssh_client_dic[host_name]
    for command in stop_commands:
        print(f"Command: {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)
        output = stdout.read().decode('utf-8')
        print(output)

# Create OpenRTiST and iperf3 servers on the server host
openrtist_server_commands = [f"cd {bash_folder} \n ./start_openrtist_server.sh {port}" for port in openrtist_ports]
iperf3_server_DL_commands = [f"cd {bash_folder} \n ./start_iperf3_server_dl.sh {port}" for port in iperf3_DL_ports]
iperf3_server_UL_commands = [f"cd {bash_folder} \n ./start_iperf3_server_ul.sh {port}" for port in iperf3_UL_ports]

server_commands = openrtist_server_commands + iperf3_server_DL_commands + iperf3_server_UL_commands
print(f"Starting servers at {experiment_setup['server'][0][0]}")
for command in server_commands:
    print(f"Command: {command}")
    stdin, stdout, stderr = server_ssh.exec_command(command, get_pty=True)
    output = stdout.read().decode('utf-8')
    print(output)
    time.sleep(5)


time.sleep(100)

# Stop all procedures on each host
bash_folder = f"~/{experiment_folder}/network-bash-scripts"
stop_commands = [f"cd {bash_folder} \n sudo ./stop_clients.sh", f"cd {bash_folder} \n sudo ./stop_servers.sh", f"cd {bash_folder} \n sudo ./stop_5G.sh", f"cd {bash_folder} \n sudo ./stop_quectel.sh"]
for host_name in all_hosts:
    print(f'Stopping processes in host {host_name}')
    ssh_client = ssh_client_dic[host_name]
    for command in stop_commands:
        print(f"Command: {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)
        output = stdout.read().decode('utf-8')
        print(output)

# End all ssh_clients
for host_name in all_hosts:
    ssh_client = ssh_client_dic[host_name]
    print(f"Closing ssh client at {host_name}")
    ssh_client.close()



