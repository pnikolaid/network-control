from parameters import hosts, experiment_identifier, bash_folder, experiment_setup, slot_length, initial_bws, bandwidth_demand_algorithm, configs_5G_folder, trajectories_folder, minimum_bandwidth

from download_QoS_files import perform_in_parallel, process_host_scp_created, create_ssh_client
from parse_QoS_files import parse_QoS_function_main
from parse_state_files import parse_state_files_function

import time
import math
import os
import pickle
from scp import SCPClient


def combine_state_QoS(states, QoSs):
    list_of_dics = []
    for slicename in states.keys():
        slice_dic = {}
        slice_dic[slicename] = {"state": states[slicename], "QoS": QoSs[slicename]}
        list_of_dics.append(slice_dic)
    return list_of_dics

def combine_state_QoS_bw(state_QoS, ul_bws, dl_bws):
    new_dictionary = {}
    sliceid = 0
    for slicename in experiment_setup.keys():
        if slicename == 'server': continue
        temp_dic_val = state_QoS[sliceid][slicename]
        ul_bw = ul_bws[sliceid]
        dl_bw =  dl_bws[sliceid]
        new_dictionary[slicename] = temp_dic_val
        new_dictionary[slicename]["resources"] = {"UL":ul_bw, "DL": dl_bw}
        sliceid += 1
    return new_dictionary

def find_bandwidth_demand(combined_dic):
    slicename = next(iter(combined_dic))

    bw_dic = {}
    bw_dic[slicename] = {}

    state = combined_dic[slicename]["state"]
    QoS = combined_dic[slicename]["QoS"]

    if bandwidth_demand_algorithm == 'basic':
        for hop in state.keys():
            value = state[hop]["PRB demand metrics"][0]
            demand = math.ceil(value)
            bw_dic[slicename][hop] = demand
    
    return bw_dic

def resolve_contention(demands):
    ul_bws = []
    dl_bws = []
    for slice_demands in demands:
        slicename = next(iter(slice_demands))
        ul_bws.append(max(slice_demands[slicename]["UL"], minimum_bandwidth))
        dl_bws.append(max(slice_demands[slicename]["DL"], minimum_bandwidth))

    ul_alloc_bws = ul_bws
    if sum(ul_bws) > 106:
        ul_alloc_bws = [5] * len(demands)
        remaining_PRBs = 106 - sum(ul_alloc_bws)
        for _ in range(len(ul_bws)):
            demand = min(ul_bws)
            argmin = ul_bws.index(min_demand)

            ul_alloc_bws[argmin] += max(min(demand - ul_alloc_bws[argmin], remaining_PRBs), 0)
            remaining_PRBs = 106 - sum(ul_alloc_bws)

    dl_alloc_bws = dl_bws
    if sum(dl_bws) > 106:
        dl_alloc_bws = [5] * len(demands)
        remaining_PRBs = 106 - sum(dl_alloc_bws)
        while remaining_PRBs:
            min_demand = min(dl_bws)
            argmin = dl_bws.index(min_demand)

            dl_alloc_bws[argmin] += max(min(min_demand - dl_alloc_bws[argmin], remaining_PRBs), 0)
            remaining_PRBs = 106 - sum(dl_alloc_bws)
    
    return ul_alloc_bws, dl_alloc_bws


parent_directory = os.path.dirname(os.getcwd())
copies_folder = os.path.join(parent_directory, '5G-copies')
os.makedirs(copies_folder, exist_ok=True)

pickle_fileame = f"{experiment_identifier}.pkl"
pickle_filepath = os.path.join(trajectories_folder, pickle_fileame)
pickle_file = open(pickle_filepath,'ab')

servername = experiment_setup["server"][0][0]
server_username = hosts[servername]['username']

state_files = ["state_dl.txt", "state_ul.txt"]
server_configs_5G_folder = f"/home/{server_username}/panos/5G-configs-logs"
local_state_files = [os.path.join(copies_folder, x) for x in state_files]
remote_state_files =[os.path.join(server_configs_5G_folder, x) for x in state_files]

bws_ul_filepath = configs_5G_folder + '/slice_bws_ul.txt'
bws_dl_filepath = configs_5G_folder + '/slice_bws_dl.txt'

def network_control_function(pipe):

    # Re-create ssh and scp clients for all hosts since each process should have its own connections
    ssh_dic = {}
    scp_dic = {}
    for host_name in hosts:
        host = hosts[host_name]
        ssh_client = create_ssh_client(host["IP"], host["port"], host["username"], host["password"])
        ssh_dic[host_name] = ssh_client
        scp_client = SCPClient(ssh_client.get_transport())
        scp_dic[host_name] = scp_client

    server_ssh_nc = ssh_dic[servername]
    server_scp_nc = scp_dic[servername]

    dl_info_list = []
    for hostname in hosts.keys():
        host_info = (hostname, ssh_dic[hostname], hosts[hostname]['remote_path'], scp_dic[hostname])
        dl_info_list.append(host_info)

    pipe.send("[Network Control] SSH and SCP clients created")
    message  = pipe.recv()

    # cleanup 5G states
    server_ssh_nc.exec_command(f"cd {bash_folder} \n sudo ./cleanup_5G_state.sh")

    # Online Control Loop!
    ul_bws = initial_bws
    dl_bws = initial_bws
    time.sleep(slot_length) # intial sleeping time to determine the effect of the initial bws

    while True:
        try:
            
            compute_start = time.time_ns()


            # Check if experiment has ended
            if pipe.poll():
                message = pipe.recv()
                if message == "Experiment ended!":
                    print(f"[Network Control] {message} Stopping control loop...")
                    break
        
            # Download QoS Files
            t2 = time.time_ns()
            perform_in_parallel(process_host_scp_created, dl_info_list)
            t3 = time.time_ns()
            #print(f"[Network Control] Downloaded QoS files in {(t3-t2)/1e6}ms")

            # Cleanup remote QoS Files
            for ssh_client in ssh_dic.values():
                ssh_client.exec_command(f"cd {bash_folder} \n ./cleanup_logs.sh")

            # Parse QoS Files
            t4 = time.time_ns()
            QoS_results = parse_QoS_function_main()
            t5 = time.time_ns()
            #print(f"[Network Control] Parsed QoS files in {(t5-t4)/1e6}ms")

            # Download 5G State
            t0 = time.time_ns()
            for i, local_path in enumerate(local_state_files):
                remote_path = remote_state_files[i]
                server_scp_nc.get(remote_path, local_path)
            t1 = time.time_ns()
            #print(f"[Network Control] Downloaded state time in {(t1-t0)/1e6}ms")

            # Cleanup remote 5G state
            server_ssh_nc.exec_command(f"cd {bash_folder} \n sudo ./cleanup_5G_state.sh")

            # Parse 5G state files
            t11 = time.time_ns()
            state_5G = parse_state_files_function() 
            t12 = time.time_ns()
            #print(f"[Network Control] Parsed 5G state files in {(t12-t11)/1e6}ms")

            # Combine state_5G and QoS_results
            state_and_QoS_list = combine_state_QoS(state_5G, QoS_results)
            # print(QoS_results)
            # print(state_and_QoS_list)

            # Estimate bandwidth demands
            bandwidth_demands = perform_in_parallel(find_bandwidth_demand, state_and_QoS_list)
            
            # Resolve resource contention
            bws_ul, bws_dl = resolve_contention(bandwidth_demands)

            # Allocate bandwidths
            bws_ul_string = ''
            for x in bws_ul: bws_ul_string += f"{x} "

            bws_dl_string = ''
            for x in bws_dl: bws_dl_string += f"{x} "

            #server_ssh_nc.exec_command(f"echo {bws_ul_string} >| {bws_ul_filepath}") # Uplink bandwidth allocation
            #server_ssh_nc.exec_command(f"echo {bws_dl_string} >| {bws_dl_filepath}") # Downlink bandwidth allocation
            #print(f"[Network Control] Allocated {bws_ul} in UL and {bws_dl} in DL")

            # Log data
            slot_info = combine_state_QoS_bw(state_and_QoS_list, bws_ul, bws_dl)
            pickle.dump(slot_info, pickle_file)

            # Sleep
            compute_overhead = (time.time_ns() - compute_start)/1e9
            #print(f"[Network Control] Loop overhead is {round(compute_overhead,2)}s")
            #print(f"[Network Control] Sleeping for {slot_length}s\n")
            time.sleep(slot_length)

        except KeyboardInterrupt:
            print("[Network Control] KeyboardInterrupt detected! Stopping control loop...")
            break # continue to another loop where so that the pipe reads the message "Experiment ended!" in order to gracefully terminate this script
    
    pickle_file.close()

    # End all scp and ssh clients
    for host_name in hosts:
        ssh_client = ssh_dic[host_name]
        scp_client = scp_dic[host_name]
        scp_client.close()
        ssh_client.close()

    print("[Network Control] SSH and SCP clients closed, process finished!")
