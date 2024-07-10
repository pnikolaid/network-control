from parameters import hosts, all_hosts, experiment_folder
from download_QoS_files import create_ssh_client

# Establish ssh clients for all hosts
ssh_client_dic = {}
for host_name in all_hosts:
    host = all_hosts[host_name]
    print(f"Creating ssh client at {host_name}")
    ssh_client = create_ssh_client(host["IP"], host["port"], host["username"], host["password"])
    ssh_client_dic[host_name] = ssh_client

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



