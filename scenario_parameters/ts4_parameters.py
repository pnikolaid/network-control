import copy
from datetime import datetime
import os
import numpy as np
import shutil

experiment_identifier = str(datetime.now().strftime("%y_%m_%d_%H_%M_%S"))
scenario_name = '4'

def keep_only_experiment_hosts(setup):

    experiment_hostnames = []
    for _, val in setup.items():
        for element in val:
            hostname = element[0]
            experiment_hostnames.append(hostname)
            
    keys_to_be_removed = []
    for key in all_hosts.keys():
        if key not in experiment_hostnames:
            keys_to_be_removed.append(key)

    for key in keys_to_be_removed:
        hosts.pop(key)

# Host parameters

experiment_folder = '$HOME/panos'   # folder that contains all required repositories (should be the same for all hosts)
bash_folder = f"{experiment_folder}/network-bash-scripts"
configs_5G_folder = f"{experiment_folder}/5G-configs-logs"
plots_folder = f"{experiment_folder}/plots"
QoS_folder = f"../QoS_files"  # contains filepath to QoS files in server
results_folder = f"../results"
experiment_results = f"{results_folder}/{scenario_name}"

os.makedirs(results_folder, exist_ok=True)
os.makedirs(experiment_results, exist_ok=True)
shutil.copyfile('./parameters.py', f'{experiment_results}/parameters.py')

parent_directory = os.path.dirname(os.getcwd())
trajectories_folder = os.path.join(parent_directory, 'trajectories')
#os.makedirs(trajectories_folder, exist_ok=True)

# gNB + CN + edge + RL algo
finarfin = {
    "IP" : '192.168.2.2',
    "port" : 22,
    "username" : 'wlab',
    "password" : 'wlab',
    "remote_path" : '/tmp',
}


# UE 1
finrod = {
    "IP" : '192.168.2.5',
    "port" : 22,
    "username" : 'expeca',
    "password" : 'expeca',
    "remote_path" : '/tmp',
}

# UE 2
fingolfin = {
    "IP" : '192.168.1.1',
    "port" : 22,
    "username" : 'wlab',
    "password" : 'wlab',
    "remote_path" : '/tmp',
}

# UE 3
forlong = {
    "IP" : '192.168.2.3',
    "port" : 22,
    "username" : 'wlab',
    "password" : 'wlab',
    "remote_path" : '/tmp',
}

# UE 4
feanor = {
    "IP" : '192.168.2.4',
    "port" : 22,
    "username" : 'expeca',
    "password" : 'expeca',
    "remote_path" : '/tmp',
}

# Host Dictionary
all_hosts = {
    "finarfin" : finarfin,
    "finrod" : finrod,
    "fingolfin" : fingolfin,
    "forlong" : forlong,
    "feanor": feanor
}

hosts = copy.deepcopy(all_hosts)

# Experiment Setup
# conaints where the server is hosted, the slices considered, the UEs that are in each slice, and the number of flows that each generates                                                                                                                          
# experiment_setup = {'server': [('finarfin',)], 'OpenRTiST': [('fingolfin', 2)], 'iperf3_DL': [('forlong', 1)], 'iperf3_UL': [('finrod', 1)] }  # tuple format: (hostname, maximum number of flows), cannot have a host used by two slices, slices must be of the form OpenRTiST, OpenRTiST-1, OpenRTiST-2  and so on
experiment_setup = {'server': [('finarfin',)],  'OpenRTiST': [('fingolfin', 2)]}
keep_only_experiment_hosts(experiment_setup)

UEs_per_slice = [len(experiment_setup[key]) for key in experiment_setup.keys() if key != 'server']  # each host has one UE thus num of UEs = num of hosts
multiple_openrtist_servers = True

# Experiment Parameters
experiment_duration = int(3600 * 1)

log_5G_state_period_in_frames = 20 # does not actually affect logging in OpenRTiST repo, only for reference
log_5G_state_period_in_ms = 10 * log_5G_state_period_in_frames

symbols_per_subframe = 28 # depends on SCS, for SCS = 30 kHz there are 28 symbols per subframe (a subframe lasts always 1 ms)
TDD_slots_ratio = {'UL':3/5 + 0.6/5, "DL": 1/5 + 0.4/5} # depends on TDD frame structure found in custom-openairinterface5g/targets/PROJECTS/GENERIC-NR-5GC/CONF/gnb.sa.band78.fr1.106PRB.usrpb210.conf

initial_bws = [int(106*x/sum(UEs_per_slice)) for x in UEs_per_slice]
leftover_bw = max(106 - sum(initial_bws), 0)
initial_bws[0] += leftover_bw
UEs_per_slice_string = ''
for x in UEs_per_slice:
    UEs_per_slice_string += f"{x} "

slicenames = []
for slicename in experiment_setup.keys():
    if slicename == 'server': continue
    slicenames.append(slicename)

initial_bws_string = ''
for x in initial_bws:
    initial_bws_string += f"{x} "

openrtist_per_flow_QoS = True

# Traffic Parameters
openrtist_mean_on_time = 10*60
openrtist_mean_off_time = 10*60
openrtist_minimum_on_time = 1*60
openrtist_minimum_off_time = 1*60

iperf3_DL_mean_on_time = 3*60
iperf3_DL_mean_off_time = 4*60
iperf3_DL_minimum_on_time = experiment_duration

iperf3_UL_mean_on_time = 2*60
iperf3_UL_mean_off_time = 3*60
iperf3_UL_minimum_on_time = experiment_duration

iperf3_DL_rate = "2M"
iperf3_UL_rate = '3M'
openrtist_rate_UL = [2.9972807843137255, 0.390072168807025, 3.19048] # UL arrival rate [mean, std, max]
openrtist_rate_DL = [0.9915711999999999, 0.13577541928699763, 1.07132]

# Network Control Parameters
slot_length = 5 # in seconds
bandwidth_demand_estimator = "static"  # "static", "basic", "vucb1", 'vucb1-per-hop', 'vucb1-per-hop-corr', 'max-estimation', 'tcp'
minimum_bandwidth = 10 # PRBs

# Configure action space and action/QoS cost
actions_UL_PRBs = list(range(minimum_bandwidth, 107, 10))
states_UL_PRBs = list(range(0, 107, 5))
#actions_DL_PRBs = [105]
actions_DL_PRBs = list(range(minimum_bandwidth, 107, 10))
states_DL_PRBs = list(range(0, 107, 5))
#actions_GPU_freq = [1500]
actions_GPU_freq = list(range(500, 1601, 100))

action_list = [actions_UL_PRBs, actions_GPU_freq, actions_DL_PRBs]

all_actions = []
for a in actions_UL_PRBs:
    for b in actions_GPU_freq:
        for c in actions_DL_PRBs:
            all_actions.append((a, b, c))

ul_prb_cost_parameter = 1
gpu_cost_parameter = 1
dl_prb_cost_parameter = 1
joint_action_cost_parameter = [ul_prb_cost_parameter, gpu_cost_parameter, dl_prb_cost_parameter]

# Desired QoS
e2e_bound = 150
ul_bound = 70
edge_bound = 20 
dl_bound = 60
delay_bounds = [ul_bound, edge_bound, dl_bound]

#vucb1 
if bandwidth_demand_estimator == 'vucb1-per-hop-corr' or 'bandwidth_demand_estimator' == 'max-estimation':
    arm_correlations = True
else:
    arm_correlations = False

random_seed = 4
