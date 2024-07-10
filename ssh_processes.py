from download_QoS_files import create_ssh_client

# Establish ssh clients for all hosts
def create_ssh_client_from_dic(all_hosts):
    ssh_client_dic = {}
    for host_name in all_hosts:
        host = all_hosts[host_name]
        print(f"Creating ssh client at {host_name}")
        ssh_client = create_ssh_client(host["IP"], host["port"], host["username"], host["password"])
        ssh_client_dic[host_name] = ssh_client