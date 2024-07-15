from parameters import hosts, all_hosts, bash_folder, experiment_setup, configs_5G_folder, initial_bws_string, UEs_per_slice_string, experiment_duration, experiment_folder
from download_QoS_files import create_ssh_client
from get_server_used_ports import get_used_ports
from create_UE_traffic_patterns import create_UE_traffic
import time
import numpy as np
import os
import matplotlib.pyplot as plt

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


ports_dict = {'OpenRTiST': openrtist_ports, 'iperf3_DL': iperf3_DL_ports, 'iperf3_UL': iperf3_UL_ports }
print("Ports:", ports_dict)

# Create Traffic Scenario on Each UE
traffic_data = {}
total_flow_activity = {'OpenRTiST': np.zeros((1, experiment_duration)), 'iperf3_DL': np.zeros((1, experiment_duration)), 'iperf3_UL': np.zeros((1, experiment_duration))}
openrtist_total_flows = np.zeros((1, experiment_duration))
iperf3_DL_total_flows = np.zeros((1, experiment_duration))
iperf3_UL_total_flows = np.zeros((1, experiment_duration))
parent_dir = os.path.dirname(os.getcwd())
plots_dir = os.path.join(parent_dir, "plots")
print("plot flod", plots_dir)

for slice in experiment_setup:
    if slice == 'server':
        continue
    for host_tuple in experiment_setup[slice]:
        host_name = host_tuple[0]
        host_num_flows = host_tuple[1]
        host_flow_type = slice
        flow_status, flow_times_durations, total_flows_over_time = create_UE_traffic(host_name, host_flow_type, host_num_flows, experiment_duration)
        ports_used_by_ue = []
        for key in total_flow_activity.keys():
         if key in slice:
            correct_key = key
            break;
        total_flow_activity[correct_key] += total_flows_over_time
        for i in range(host_num_flows):
            ports_used_by_ue.append(ports_dict[correct_key][0])
            ports_dict[correct_key].pop(0)

        traffic_data[host_name] = (host_flow_type, ports_used_by_ue, flow_times_durations)

print(traffic_data)
        
for host_name in traffic_data.keys():
    for triple_tuple in traffic_data[host_name]:
        slice = triple_tuple[0]






for slice_type in total_flow_activity.keys():
    plt.figure(figsize=(15, 6))
    plt.step(list(range(experiment_duration)), list(total_flow_activity[slice_type][0]))
    plt.xlabel('Time')
    plt.ylabel('Number of Active Flows')
    plt.title(f'gNB -- {slice_type}')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot as PDF in the plots folder
    plt.savefig(plots_dir + f'/gNB_{slice_type}_total_active_flows.pdf', dpi=300)  # Adjust dpi as needed
    plt.close()

input("Traffic patterns created! \nPress Enter to continue...")

# Stop all procedures on each host
stop_commands = [f"cd {bash_folder} \n sudo ./stop_clients.sh", f"cd {bash_folder} \n sudo ./stop_servers.sh", f"cd {bash_folder} \n sudo ./stop_5G.sh", f"cd {bash_folder} \n sudo ./stop_quectel.sh"]
for host_name in all_hosts:
    print(f'Stopping processes in host {host_name}\n')
    ssh_client = ssh_client_dic[host_name]
    for command in stop_commands:
        print(f"({host_name}) Issuing command:\n {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)
        output = stdout.read().decode('utf-8')
        print(output)

input(f"Any clients/servers, quectel modules and 5G systems have been stopped to reset the setup! \nPress Enter to continue...")

# Reset slices_dl.txt, slice_bws_ul.txt, state_dl.txt, state_ul.txt and UEs_per_slice.txt
ues_per_slice_filepath = configs_5G_folder + '/UEs_per_slice.txt'
bws_dl_filepath = configs_5G_folder + '/slice_bws_dl.txt'
bws_ul_filepath = configs_5G_folder + '/slice_bws_ul.txt'
state_dl_filepath = configs_5G_folder + '/state_dl.txt'
state_ul_filepath = configs_5G_folder + '/state_ul.txt'
reset_5G_commands = [f"echo 666 0 >| {ues_per_slice_filepath}", f"echo 106 0 >| {bws_dl_filepath}", f"echo 106 0 >| {bws_ul_filepath}"]

for command in reset_5G_commands:
    print(f"({server_name}) Issuing command:\n {command}")
    stdin, stdout, stderr = server_ssh.exec_command(command, get_pty=True)
    output = stdout.read().decode('utf-8')
    print(output)
    
input(f"Files in 5G-configs-logs reseted \nPress Enter to continue...")

# Create OpenRTiST and iperf3 servers on the server host
openrtist_server_commands = [f"cd {bash_folder} \n ./start_openrtist_server.sh {port}" for port in openrtist_ports]
iperf3_server_DL_commands = [f"cd {bash_folder} \n ./start_iperf3_server_dl.sh {port}" for port in iperf3_DL_ports]
iperf3_server_UL_commands = [f"cd {bash_folder} \n ./start_iperf3_server_ul.sh {port}" for port in iperf3_UL_ports]

server_commands = openrtist_server_commands + iperf3_server_DL_commands + iperf3_server_UL_commands
print(f"Starting servers at {experiment_setup['server'][0][0]}")
for command in server_commands:
    print(f"({server_name}) Issuing command:\n {command}")
    stdin, stdout, stderr = server_ssh.exec_command(command, get_pty=True)
    output = stdout.read().decode('utf-8')
    print(output)
    time.sleep(5)

input(f"All required iperf3 and OpenRTiST servers are up at {server_name}! \nPress Enter to continue...")

# Start 5G system
start_CN_command= [f"cd {bash_folder} \n sudo ./start_5G_CN.sh"]
start_gNB_command = [f"cd {bash_folder} \n ./start_5G_gNB.sh"]

server_commands = start_CN_command + start_gNB_command
print(f"Starting servers at {experiment_setup['server'][0][0]}")
for command in server_commands:
    print(f"({host_name}) Issuing command:\n {command}")
    stdin, stdout, stderr = server_ssh.exec_command(command, get_pty=True)
    output = stdout.read().decode('utf-8')
    print(output)
    time.sleep(5)

input(f"The 5G system is up at {server_name}! \nPress Enter to continue...")

# Initialize slices_dl.txt, slice_bws_ul.txt, state_dl.txt, state_ul.txt and UEs_per_slice.txt
ues_per_slice_filepath = configs_5G_folder + '/UEs_per_slice.txt'
bws_dl_filepath = configs_5G_folder + '/slice_bws_dl.txt'
bws_ul_filepath = configs_5G_folder + '/slice_bws_ul.txt'
state_dl_filepath = configs_5G_folder + '/state_dl.txt'
state_ul_filepath = configs_5G_folder + '/state_ul.txt'
reset_5G_commands = [f"echo {UEs_per_slice_string} >| {ues_per_slice_filepath}", f"echo {initial_bws_string} >| {bws_dl_filepath}", f"echo {initial_bws_string} >| {bws_ul_filepath}"]

for command in reset_5G_commands:
    print(f"({server_name}) Issuing command:\n {command}")
    stdin, stdout, stderr = server_ssh.exec_command(command, get_pty=True)
    output = stdout.read().decode('utf-8')
    print(output)
    
input(f"The initial values for the 5G txt files are set! \nPress Enter to continue...")


# Connect the UEs to the 5G system

# Their order of connection needs to be correct since their uid is incremental
# So first we need to start all the UEs of the first slice, then all the UEs of the second slice, then all the UEs of the third slice and so on...
# This is necessary since OAI does not expose the NSSAI values of a UE at the MAC layer so we cannot assoicate UEs to a slice only based on their UID
turn_on_quectel_command = f"cd {bash_folder} \nsudo ./start_quectel.sh"
for slice in experiment_setup.keys():
    if slice == 'server':
        # not really a slice, please skip
        continue
    for ue_tuple in experiment_setup[slice]:
        host_name = ue_tuple[0]
        print(f"({host_name}) Issuing command\n {turn_on_quectel_command}")
        ue_ssh_client = ssh_client_dic[host_name]
        stdin, stdout, stderr = ue_ssh_client.exec_command(turn_on_quectel_command, get_pty=True)
        output = stdout.read().decode('utf-8')
        print(output)
        time.sleep(10)

input(f"The quectel modules are on and the UEs have connected to the 5G system! \nPress Enter to continue...")


# Generate Traffic
trigger_times = [2, 4, 5, 600]

start_time = time.time()
end_time = experiment_duration + 10

triggered = set()
try:
    while True:
        current_time = time.time()

        elapsed_time = current_time - start_time
        for t in trigger_times:
            if t not in triggered and elapsed_time >= t:
                print(f"hello at t={t} seconds")
                triggered.add(t)
        
        # Break the loop if all times have been triggered
        if len(triggered) == len(trigger_times):
            break
        
        time.sleep(0.1)  # Sleep briefly to avoid busy-waiting
except KeyboardInterrupt:
        print("Stopped by user")

# Stop all procedures on each host
stop_commands = [f"cd {bash_folder} \n sudo ./stop_clients.sh", f"cd {bash_folder} \nsudo ./stop_servers.sh", f"cd {bash_folder} \n sudo ./stop_5G.sh", f"cd {bash_folder} \n sudo ./stop_quectel.sh"]
for host_name in all_hosts:
    print(f'Stopping processes in host {host_name}')
    ssh_client = ssh_client_dic[host_name]
    for command in stop_commands:
        print(f"Command: {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)
        output = stdout.read().decode('utf-8')
        print(output)

# Reset slices_dl.txt, slice_bws_ul.txt, state_dl.txt, state_ul.txt and UEs_per_slice.txt
ues_per_slice_filepath = configs_5G_folder + '/UEs_per_slice.txt'
bws_dl_filepath = configs_5G_folder + '/slice_bws_dl.txt'
bws_ul_filepath = configs_5G_folder + '/slice_bws_ul.txt'
state_dl_filepath = configs_5G_folder + '/state_dl.txt'
state_ul_filepath = configs_5G_folder + '/state_ul.txt'
reset_5G_commands = [f"echo 999 0 >| {ues_per_slice_filepath}", f"echo 106 0 >| {bws_dl_filepath}", f"echo 106 0 >| {bws_ul_filepath}"]

# End all ssh_clients
for host_name in all_hosts:
    ssh_client = ssh_client_dic[host_name]
    print(f"Closing ssh client at {host_name}")
    ssh_client.close()



