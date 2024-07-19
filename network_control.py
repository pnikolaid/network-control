from parameters import hosts, all_hosts, bash_folder, experiment_setup, initial_bws_string, UEs_per_slice_string, experiment_duration, iperf3_DL_rate, iperf3_UL_rate, QoS_folder, slot_length
from download_QoS_files import perform_in_parallel, process_host_scp_created, create_ssh_client
from scp import SCPClient
from parse_QoS_files import parse_QoS_function_main
import time
import os 

parent_directory = os.path.dirname(os.getcwd())
copies_folder = os.path.join(parent_directory, '5G-copies')
os.makedirs(copies_folder, exist_ok=True)

servername = experiment_setup["server"][0][0]
server_username = hosts[servername]['username']

state_files = ["state_dl.txt", "state_ul.txt"]
server_configs_5G_folder = f"/home/{server_username}/panos/5G-configs-logs"
local_state_files = [os.path.join(copies_folder, x) for x in state_files]
remote_state_files =[os.path.join(server_configs_5G_folder, x) for x in state_files]

def network_control_function():

    # Re-create ssh and scp clients for all hosts since each process should have its own connections
    ssh_dic = {}
    scp_dic = {}
    for host_name in hosts:
        host = hosts[host_name]
        print(f"Creating ssh client at {host_name}")
        ssh_client = create_ssh_client(host["IP"], host["port"], host["username"], host["password"])
        ssh_dic[host_name] = ssh_client
        scp_client = SCPClient(ssh_client.get_transport())
        scp_dic[host_name] = scp_client

    server_ssh_nc = ssh_dic[servername]
    server_scp_nc = scp_dic[servername]

    experiment_start_time = time.time()
    experiment_end_time = experiment_start_time + experiment_duration
    current_time = experiment_start_time

    dl_info_list = []
    for hostname in hosts.keys():
        host_info = (hostname, ssh_dic[hostname], hosts[hostname]['remote_path'], scp_dic[hostname])
        dl_info_list.append(host_info)

    # cleanup 5G state
    server_ssh_nc.exec_command(f"cd {bash_folder} \n sudo ./cleanup_5G_state.sh")

    while current_time <= experiment_end_time:

        # Download State
        print(f"[Network-control] Downloading the state...")
        t0 = time.time_ns()
        for i, local_path in enumerate(local_state_files):
            remote_path = remote_state_files[i]
            server_scp_nc.get(remote_path, local_path)
        t1 = time.time_ns()
        print(f"[Network-control] Download state time: {(t1-t0)/1e6}ms")

        # Cleanup remote 5G state
        server_ssh_nc.exec_command(f"cd {bash_folder} \n sudo ./cleanup_5G_state.sh")

        # Sleep
        print(f"[Network-control] Sleeping for {slot_length}s...")
        time.sleep(slot_length)

        # Download QoS Files
        print(f"[Network-control] Downloading the QoS files...")
        t2 = time.time_ns()
        perform_in_parallel(process_host_scp_created, dl_info_list)
        t3 = time.time_ns()
        print(f"[Network-control] Download QoS time: {(t3-t2)/1e6}ms")

        # Cleanup remote QoS Files
        for ssh_client in ssh_dic.values():
            ssh_client.exec_command(f"cd {bash_folder} \n ./cleanup_logs.sh")

        # Parse QoS Files
        t4 = time.time_ns()
        QoS_results = parse_QoS_function_main()
        t5 = time.time_ns()
        print(f"[Network-control] Parse QoS time: {(t5-t4)/1e6}ms")

        current_time = time.time()
    
    print("Network Control process finished")


if __name__ == '__main__':
    print("yolo")