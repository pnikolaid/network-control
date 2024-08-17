from parameters import hosts, all_hosts, bash_folder, experiment_setup, configs_5G_folder, initial_bws_string, UEs_per_slice_string, experiment_duration, iperf3_DL_rate, iperf3_UL_rate, QoS_folder
from download_QoS_files import create_ssh_client, process_host_scp_created, perform_in_parallel
from scp import SCPClient
from get_server_used_ports import get_used_ports
from create_UE_traffic_patterns import create_UE_traffic
import time
from datetime import datetime
import numpy as np
import os
import matplotlib.pyplot as plt
import copy
import glob
import multiprocessing
from network_control import network_control_function

# Establish ssh and scp clients for all hosts
ssh_client_dic = {}
scp_client_dic = {}
for host_name in all_hosts:
    host = all_hosts[host_name]
    print(f"Creating ssh client at {host_name}")
    ssh_client = create_ssh_client(host["IP"], host["port"], host["username"], host["password"])
    ssh_client_dic[host_name] = ssh_client
    scp_client = SCPClient(ssh_client.get_transport())
    scp_client_dic[host_name] = scp_client

download_tuple_list = []
for hostname in hosts.keys():
    host_info = (hostname, ssh_client_dic[hostname], hosts[hostname]['remote_path'], scp_client_dic[hostname])
    download_tuple_list.append(host_info)

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
original_ports_dict = copy.deepcopy(ports_dict)
openrtist_ports_copy = openrtist_ports.copy()
iperf3_DL_ports_copy = iperf3_DL_ports.copy()
iperf3_UL_ports_copy = iperf3_UL_ports.copy()

# Find ports per UE
ports_dict_per_ue = {}
for key in experiment_setup.keys():
    if key == 'server': continue

    for tuple in experiment_setup[key]:
        (ue_name, n_flows) = tuple
        if 'OpenRTiST' in key:
            # extract n_flow items from openrtist ports
            ue_ports, openrtist_ports_copy = openrtist_ports_copy[:n_flows], openrtist_ports_copy[n_flows:]

        if 'iperf3_DL' in key:
             ue_ports, iperf3_DL_ports_copy = iperf3_DL_ports_copy[:n_flows], iperf3_DL_ports_copy[n_flows:]

        if 'iperf3_UL' in key:
             ue_ports, iperf3_UL_ports_copy = iperf3_UL_ports_copy[:n_flows], iperf3_UL_ports_copy[n_flows:]
        ports_dict_per_ue[ue_name] = ue_ports


# Create Traffic Scenario on Each UE
parent_dir = os.path.dirname(os.getcwd())
plots_dir = os.path.join(parent_dir, "plots")
files = glob.glob(f'{plots_dir}/*')
for f in files:
    os.remove(f)

traffic_data = {}
total_flow_activity = {'OpenRTiST': np.zeros((1, experiment_duration)), 'iperf3_DL': np.zeros((1, experiment_duration)), 'iperf3_UL': np.zeros((1, experiment_duration))}
openrtist_total_flows = np.zeros((1, experiment_duration))
iperf3_DL_total_flows = np.zeros((1, experiment_duration))
iperf3_UL_total_flows = np.zeros((1, experiment_duration))


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

traffic_command_info = []
for host_name in traffic_data.keys():
    triple_tuple = traffic_data[host_name]
    slice = triple_tuple[0]
    ports = triple_tuple[1]
    flow_info = triple_tuple[2]
    for count, flow in enumerate(flow_info):
        port = ports[count]
        for double_tuple in flow:
            start_time = double_tuple[0]
            duration = double_tuple[1]
            command_info = [start_time, duration, host_name, slice, port]
            traffic_command_info.append(command_info)

traffic_command_info.sort()

traffic_commands = []
for info in traffic_command_info:
    start_time = info[0]
    duration = info[1]
    host_name = info[2]
    slice = info[3]
    port = info[4]
    for slice_type in total_flow_activity.keys():
        if slice_type in slice:
            break;
    if slice_type == 'OpenRTiST':
        script_name = 'start_openrtist_client.sh'
        command = f"./{script_name} {port} {duration}"
    elif slice_type == 'iperf3_DL':
        script_name = 'start_iperf3_client_dl.sh'
        command = f"./{script_name} {port} {duration} {iperf3_DL_rate}"
    elif slice_type == 'iperf3_UL':
        script_name = 'start_iperf3_client_ul.sh'
        command = f"./{script_name} {port} {duration} {iperf3_UL_rate}"
    traffic_commands.append([start_time, host_name, command])

for command in traffic_commands:
    command[2] = f"cd {bash_folder} \n " + command[2]
    print(command)

print("Traffic patterns and traffic commands created!")

# Clear QoS folder
files = glob.glob(f'{QoS_folder}/*')
for f in files:
    os.remove(f)

# Stop all procedures on each host
stop_commands = [f"cd {bash_folder}\n sudo ./stop_clients.sh", f"cd {bash_folder} \n sudo ./stop_servers.sh", f"cd {bash_folder} \n sudo ./stop_5G.sh", f"cd {bash_folder} \n sudo ./stop_quectel.sh", f"cd {bash_folder} \n yes | ./delete_iperf3_logs.sh", f"cd {bash_folder} \n ./cleanup_logs.sh"]
for host_name in all_hosts:
    print(f'Stopping processes in host {host_name}\n')
    ssh_client = ssh_client_dic[host_name]
    for command in stop_commands:
        print(f"({host_name}) Issuing command:\n {command}")
        stdin, stdout, stderr = ssh_client.exec_command(command, get_pty=True)
        output = stdout.read().decode('utf-8')
        print(output)

print(f"Any clients/servers, quectel modules and 5G systems have been stopped to reset the setup! All logs also been erased!")

# Reset slices_dl.txt, slice_bws_ul.txt, state_dl.txt, state_ul.txt and UEs_per_slice.txt
ues_per_slice_filepath = configs_5G_folder + '/UEs_per_slice.txt'
bws_dl_filepath = configs_5G_folder + '/slice_bws_dl.txt'
bws_ul_filepath = configs_5G_folder + '/slice_bws_ul.txt'
# state_dl_filepath = configs_5G_folder + '/state_dl.txt'
# state_ul_filepath = configs_5G_folder + '/state_ul.txt'
reset_5G_commands = [f"echo 666 0 >| {ues_per_slice_filepath}", f"echo 106 0 >| {bws_dl_filepath}", f"echo 106 0 >| {bws_ul_filepath}", f"cd {bash_folder} \n sudo ./cleanup_5G_state.sh", "yes | docker volume prune"]

for command in reset_5G_commands:
    print(f"({server_name}) Issuing command:\n {command}")
    stdin, stdout, stderr = server_ssh.exec_command(command, get_pty=True)
    output = stdout.read().decode('utf-8')
    print(output)
    
print(f"Files in 5G-configs-logs reseted and state_dl.txt and state_ul.txt cleared!")

# Create OpenRTiST and iperf3 servers on the server host
openrtist_server_commands = [f"cd {bash_folder} \n ./start_openrtist_server.sh {port}" for port in original_ports_dict['OpenRTiST']]
iperf3_server_DL_commands = [f"cd {bash_folder} \n ./start_iperf3_server_dl.sh {port}" for port in original_ports_dict['iperf3_DL']]
iperf3_server_UL_commands = [f"cd {bash_folder} \n ./start_iperf3_server_ul.sh {port}" for port in original_ports_dict['iperf3_UL']]

server_commands = openrtist_server_commands + iperf3_server_DL_commands + iperf3_server_UL_commands
print(f"Starting servers at {server_name}")
print(server_commands)
for command in server_commands:
    print(f"({server_name}) Issuing command:\n {command}")
    stdin, stdout, stderr = server_ssh.exec_command(command, get_pty=True)
    output = stdout.read().decode('utf-8')
    print(output)
    time.sleep(5)

print(f"All required iperf3 and OpenRTiST servers are up at {server_name}!")

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
    time.sleep(30)

print(f"The 5G system is up at {server_name}!")

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
    
print(f"The initial values for the 5G txt files are set!")


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

print(f"The quectel modules are on and the UEs have connected to the 5G system!")



# Establish pipe between the parent traffic generator process and the child process called network controls 
traffic_end, control_end = multiprocessing.Pipe()

# Define RL process to be run in parallel with traffic generator
control_process = multiprocessing.Process(target=network_control_function, args=(control_end, ports_dict_per_ue))

# Start RL process
control_process.start()
message = traffic_end.recv()
print(message)

# input(f"Setup is complete!! \nPress <Enter> to start the experiment...")


# Generate Traffic by issuing the commands in traffic_commands = [start_time, host_name, command]
experiment_start_time = time.time()
experiment_end_time = experiment_start_time + experiment_duration
current_time = experiment_start_time
commands_issued = 0
readable_start_time = datetime.now().strftime("%H:%M:%S")
print(f"Experiment duration: {experiment_duration}s")
print(f"[Traffic Generator] ({readable_start_time} -> 0s)")

traffic_end.send("Experiment started!") # notify control process to start the while control loop

try:
    while current_time <= experiment_end_time :
        current_time = time.time()
        elapsed_time = current_time - experiment_start_time
        for command in traffic_commands[commands_issued:]:
            if elapsed_time < command[0]:
                # Next command starts in the future
                break
            else:
                # The command needs to be issued ASAP
                host_name = command[1]
                ue_ssh_client = ssh_client_dic[host_name]
                stdin, stdout, stderr = ue_ssh_client.exec_command(command[2], get_pty=False)
                # stdout.channel.set_combine_stderr(True)
                # output = stdout.read().decode('utf-8')
                # print(f"output: {output}")
                
                short_command = command[2].split('\n', 1)[1].strip()
                readable_time = datetime.now().strftime("%H:%M:%S")
                elapsed_time_3digits = "{:.3f}".format(elapsed_time)
                print(f"[Traffic Generator] ({host_name} {readable_time} -> {elapsed_time_3digits}s vs {command[0]}s): {short_command}")

                commands_issued += 1
        
        time.sleep(0.1)  # Sleep briefly to avoid busy-waiting
except KeyboardInterrupt:
        print("Experiment stopped by user!")

traffic_end.send("Experiment ended!")
control_process.join()
print(f"Desired and actual experiment time: {experiment_duration}s vs {time.time()-experiment_start_time}s")

# Download QoS files
t0 = time.time_ns()
perform_in_parallel(process_host_scp_created, download_tuple_list)
t1 = time.time_ns()
print(f"Download time: {(t1-t0)/1e6}ms")

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

# End all scp and ssh clients
for host_name in all_hosts:
    print(f"Closing scp and ssh client at {host_name}")
    ssh_client = ssh_client_dic[host_name]
    scp_client = scp_client_dic[host_name]
    scp_client.close()
    ssh_client.close()

print("Script has ended!")
