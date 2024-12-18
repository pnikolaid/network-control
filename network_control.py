from parameters import hosts, bash_folder, experiment_setup, slot_length, initial_bws, bandwidth_demand_estimator, configs_5G_folder, minimum_bandwidth, all_actions, arm_correlations, e2e_bound, delay_bounds, action_list, states_UL_PRBs, states_DL_PRBs, experiment_results, joint_action_cost_parameter

from download_QoS_files import perform_in_parallel, process_host_scp_created, create_ssh_client
from parse_QoS_files import parse_QoS_function_main
from parse_state_files import parse_state_files_function
import time
import math
import os
import pickle
from scp import SCPClient
from collections import defaultdict
import bisect
from ucb1 import vUCB1

vucb1_dic = {}
vucb1_dic_dl = {}
vcub1_dic_edge = {}
vucb1_dic_ul = {}
vucb1_per_hop_dics = [vucb1_dic_dl, vcub1_dic_edge, vucb1_dic_ul]

tcp_resources = []
for hop in range(len(action_list)):
    tcp_initialization = min(x for x in action_list[hop] if x >= action_list[hop][-1]/2)
    tcp_resources.append(tcp_initialization)


def update_bandwidth_demand_estimator(trajectory_dic, qos_results):
    for slicename in trajectory_dic:
        if 'OpenRTiST' in slicename:
            qos_reward = 1
            for flow in qos_results[slicename]:
                if 'mean' not in qos_results[slicename][flow]['E2E']:
                    qos_reward = 0
                    break
                if qos_results[slicename][flow]['E2E']['mean'] > e2e_bound:
                    qos_reward = 0
                    break
            trajectory_dic[slicename]['QoS_reward'] = qos_reward
            
            if bandwidth_demand_estimator == 'vucb1':
                state  = trajectory_dic[slicename]['state']
                arm_selected = (trajectory_dic[slicename]["UL"], trajectory_dic[slicename]['EDGE'], trajectory_dic[slicename]["DL"])
                reward = vucb1_dic[state].update(arm_selected, qos_reward)
                trajectory_dic[slicename]['reward'] = reward

            elif bandwidth_demand_estimator == 'vucb1-per-hop' or bandwidth_demand_estimator == 'vucb1-per-hop-corr' or bandwidth_demand_estimator == 'max-estimation':
                hops = ["UL", "EDGE", "DL"]
                arm_selected = []
                trajectory_dic[slicename]['reward'] = {}
                for k, hop in enumerate(hops):
                    hop_qos_reward = 1
                    for flow in qos_results[slicename]:
                        if 'mean' not in qos_results[slicename][flow][hop]:
                            hop_qos_reward = 0
                            break
                        if qos_results[slicename][flow][hop]['mean'] > delay_bounds[k]:
                            hop_qos_reward = 0
                            break
                    hop_arm_selected = trajectory_dic[slicename][hop]
                    arm_selected.append(hop_arm_selected)
                    hop_state  = trajectory_dic[slicename]['state'][k]
                    hop_reward = vucb1_per_hop_dics[k][hop_state].update(hop_arm_selected, hop_qos_reward)
                    trajectory_dic[slicename]['reward'][hops[k]] = hop_reward
            
            elif bandwidth_demand_estimator == 'tcp':
                hops = ["UL", "EDGE", "DL"]
                for k, hop in enumerate(hops):
                    hop_qos_reward = 1
                    for flow in qos_results[slicename]:
                        if 'mean' not in qos_results[slicename][flow][hop]:
                            hop_qos_reward = 0
                            break
                        if qos_results[slicename][flow][hop]['mean'] > delay_bounds[k]:
                            hop_qos_reward = 0
                            break
                    if hop_qos_reward == 0:
                        candidates = [x for x in action_list[k] if x >= tcp_resources[k]*2] # all hop actions with double value
                        if not candidates: candidates = [max(action_list[k])] # if cannot double any further consider max hop action
                        tcp_resources[k] = min(candidates) # pick smallest candidate
                    else:
                        candidates = [x for x in action_list[k] if x < tcp_resources[k]] # find smaller hop actions
                        if not candidates: candidates = [min(action_list[k])]
                        tcp_resources[k] = max(candidates)
                

def find_smallest_greater(x, array):
    index = bisect.bisect_right(array, x)
    index = min(index, len(array) - 1)
    return array[index]

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
        new_dictionary[slicename]["resources"] = {"UL": ul_bw, "DL": dl_bw}
        sliceid += 1
    return new_dictionary

def parse_slot_info(info, ports_per_ue):

    active_flows_per_ue = defaultdict(int)
    for slicename in info:
        active_flows = [key for key in info[slicename]["QoS"].keys()]
        for port_id in active_flows:
            for ue in ports_per_ue.keys():
                ue_ports = ports_per_ue[ue]
                if int(port_id) in ue_ports:
                    active_flows_per_ue[ue] += 1

    results_list = []
    for slicename in info:
        slice_list = [slicename]

        state = info[slicename]["state"]
        hops = ["UL", "DL"]

        for hop in hops:
            mean_PRBs_per_flow = state[hop]['PRB demand per flow metrics'][0]
            max_PRBs_per_flow = state[hop]['PRB demand per flow metrics'][2]

            mean_slice_demand = 0
            max_slice_demand = 0
            for idx, tuple in enumerate(experiment_setup[slicename]):
                uename = tuple[0]
                mean_slice_demand += mean_PRBs_per_flow[idx] * active_flows_per_ue[uename]
                max_slice_demand += max_PRBs_per_flow[idx] * active_flows_per_ue[uename]

            info[slicename]["state"][hop]["mean PRB slice demand"] = math.ceil(mean_slice_demand)
            info[slicename]["state"][hop]["max PRB slice demand"] = math.ceil(max_slice_demand)
        
            slice_list.append(math.ceil(mean_slice_demand))
            slice_list.append(math.ceil(max_slice_demand))
        results_list.append(slice_list) # each slice_list = [slicename, ul_mean_bw, ul_max_bw, dl_mean_bw, dl_max_bw]
    return info, results_list

def find_bandwidth_demand(slice_list):
    bw_dic = {}
    slicename = slice_list[0]
    bw_dic[slicename] = {}
    if bandwidth_demand_estimator == 'basic':
        bw_dic[slicename]["UL"] = slice_list[1]
        bw_dic[slicename]["DL"] = slice_list[3]

    elif bandwidth_demand_estimator == 'vucb1':
        mean_UL_PRBs = find_smallest_greater(slice_list[1], states_UL_PRBs)
        mean_DL_PRBs = find_smallest_greater(slice_list[3], states_DL_PRBs)
        state = (mean_UL_PRBs, mean_DL_PRBs)
        if state not in vucb1_dic:
            vucb1_dic[state] = vUCB1(all_actions, joint_action_cost_parameter, arm_correlations)
        arm_selected = vucb1_dic[state].select_arm()
        bw_dic[slicename]["UL"] = arm_selected[0]
        bw_dic[slicename]['EDGE'] = arm_selected[1]
        bw_dic[slicename]["DL"] = arm_selected[2]
        bw_dic[slicename]["state"] = state
    
    elif bandwidth_demand_estimator == 'vucb1-per-hop' or bandwidth_demand_estimator == 'vucb1-per-hop-corr' or bandwidth_demand_estimator == 'max-estimation':
        mean_UL_PRBs = find_smallest_greater(slice_list[1], states_UL_PRBs)
        mean_DL_PRBs = find_smallest_greater(slice_list[3], states_DL_PRBs)
        state_ul = mean_UL_PRBs
        state_edge = mean_UL_PRBs
        state_dl = mean_DL_PRBs
        state_components = [state_ul, state_edge, state_dl]
        if bandwidth_demand_estimator == 'max-estimation': state_components = [0, 0, 0]
        hops = ['UL', 'EDGE', 'DL']
        for k, state_hop in enumerate(state_components):
            if state_hop not in vucb1_per_hop_dics[k]:
                vucb1_per_hop_dics[k][state_hop] = vUCB1(action_list[k], joint_action_cost_parameter[k], arm_correlations)
            hop_arm_selected = vucb1_per_hop_dics[k][state_hop].select_arm()
            hop = hops[k]
            bw_dic[slicename][hop] = hop_arm_selected
        bw_dic[slicename]["state"] = state_components
    
    elif bandwidth_demand_estimator == 'static':
        for count, key in enumerate(experiment_setup):
            if key == slicename: break
        count -= 1
        bw_dic[slicename]['UL'] = initial_bws[count]
        bw_dic[slicename]['DL'] = initial_bws[count]
        bw_dic[slicename]['EDGE'] = 1600

    elif bandwidth_demand_estimator == 'tcp':
        bw_dic[slicename]['UL'] = tcp_resources[0]
        bw_dic[slicename]['EDGE'] = tcp_resources[1]
        bw_dic[slicename]['DL'] = tcp_resources[2]

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

pickle_fileame = f"{bandwidth_demand_estimator}.pkl"
pickle_filepath = os.path.join(experiment_results, pickle_fileame)
if os.path.exists(pickle_filepath): os.remove(pickle_filepath)
pickle_file = open(pickle_filepath,'ab')

servername = experiment_setup["server"][0][0]
server_username = hosts[servername]['username']

state_files = ["state_dl.txt", "state_ul.txt"]
server_configs_5G_folder = f"/home/{server_username}/panos/5G-configs-logs"
local_state_files = [os.path.join(copies_folder, x) for x in state_files]
remote_state_files =[os.path.join(server_configs_5G_folder, x) for x in state_files]

bws_ul_filepath = configs_5G_folder + '/slice_bws_ul.txt'
bws_dl_filepath = configs_5G_folder + '/slice_bws_dl.txt'

def network_control_function(pipe, ports_per_ue):

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
    bws_ul = initial_bws
    bws_dl = initial_bws
    gpu_freq = 1600
    time.sleep(slot_length) # intial sleeping time to determine the effect of the initial bws
    completed_loops = 0
    total_overhead = 0
    trajectory_dics = []
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

            # Update the state of the learning algorithm
            if trajectory_dics:
                update_bandwidth_demand_estimator(trajectory_dics[-1], QoS_results)
                print(trajectory_dics[-1])
                print(QoS_results)

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

            # Find the input features to the learning algorithm and 
            slot_info = combine_state_QoS_bw(state_and_QoS_list, bws_ul, bws_dl)
            new_slot_info, features = parse_slot_info(slot_info, ports_per_ue)
            new_slot_info["GPU_FREQ"] = gpu_freq # this is common for all slices
            pickle.dump(new_slot_info, pickle_file)

            # Estimate bandwidth demands
            action_dic = perform_in_parallel(find_bandwidth_demand, features)

            # Transfrom dictionary
            trajectory_dic = {}
            for item in action_dic:
                slicename = next(iter(item))
                trajectory_dic[slicename] = item[slicename]
            trajectory_dics.append(trajectory_dic)

            # Find gpu_freq
            for slicename in trajectory_dic:
                if slicename in 'OpenRTiST':
                    gpu_freq = trajectory_dic[slicename]['EDGE']

            # Resolve resource contention
            bws_ul, bws_dl = resolve_contention(action_dic)

            #bws_ul, bws_dl = initial_bws, initial_bws

            # Allocate bandwidths
            bws_ul_string = ''
            for x in bws_ul: bws_ul_string += f"{x} "

            bws_dl_string = ''
            for x in bws_dl: bws_dl_string += f"{x} "

            server_ssh_nc.exec_command(f"echo {bws_ul_string} >| {bws_ul_filepath}") # Uplink bandwidth allocation
            server_ssh_nc.exec_command(f"echo {bws_dl_string} >| {bws_dl_filepath}") # Downlink bandwidth allocation
            #print(f"[Network Control] Allocated {bws_ul} in UL and {bws_dl} in DL")
            
            # Change GPU frequency
            server_ssh_nc.exec_command(f"sudo nvidia-smi -lgc {gpu_freq}")

            completed_loops += 1

            # Sleep
            compute_overhead = (time.time_ns() - compute_start) / 1e9
            total_overhead += compute_overhead
            avg_overhead = total_overhead/completed_loops
            print(f"[Network Control] Control loop overhead, current {round(compute_overhead, 2)}s and average {round(avg_overhead, 2)}s")
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
