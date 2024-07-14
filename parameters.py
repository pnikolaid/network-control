import copy

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
remote_path = '/tmp'  # contains filepath to QoS files in each host
local_path = f"{experiment_folder}/QoS_files"  # contains filepath to QoS files in server

# gNB + CN + edge + RL algo
finarfin = {
    "IP" : '192.168.2.2',
    "port" : 22,
    "username" : 'wlab',
    "password" : 'wlab',
    "remote_path" : remote_path,
    "local_path" : local_path
}


# UE 1
finrod = {
    "IP" : '192.168.2.5',
    "port" : 22,
    "username" : 'expeca',
    "password" : 'expeca',
    "remote_path" : remote_path,
    "local_path" : local_path
}

# UE 2
fingolfin = {
    "IP" : '192.168.1.1',
    "port" : 22,
    "username" : 'wlab',
    "password" : 'wlab',
    "remote_path" : remote_path,
    "local_path" : local_path
}

# UE 3
forlong = {
    "IP" : '192.168.2.3',
    "port" : 22,
    "username" : 'wlab',
    "password" : 'wlab',
    "remote_path" : remote_path,
    "local_path" : local_path
}

# UE 4
feanor = {
    "IP" : '192.168.2.4',
    "port" : 22,
    "username" : 'expeca',
    "password" : 'expeca',
    "remote_path" : remote_path,
    "local_path" : local_path
}

# Host Dictionary
all_hosts = {
    "finarfin" : finarfin,
    "finrod" : finrod,
    "fingolfin" : fingolfin,
    "forlong" : forlong,
    "feanor" : feanor
}

hosts = copy.deepcopy(all_hosts)

# Experiment Setup
# conaints where the server is hosted, the slices considered, the UEs that are in each slice, and the number of flows that each generates                                                                                                                          
experiment_setup = {'server': [('finarfin',)], 'OpenRTiST-1': [('feanor', 2)], 'OpenRTiST-2': [('fingolfin', 1)], 'iperf3_UL': [('finrod', 3)] }  # tuple format: (hostname, maximum number of flows), cannot have a host used by two slices, slices must be of the form OpenRTiST, OpenRTiST-1, OpenRTiST-2  and so on
keep_only_experiment_hosts(experiment_setup)

UEs_per_slice = [len(experiment_setup[key]) for key in experiment_setup.keys() if key != 'server']  # each host has one UE thus num of UEs = num of hosts

# Experiment Parameters
experiment_duration = 3600
initial_bws = [int(106*x/sum(UEs_per_slice)) for x in UEs_per_slice]
leftover_bw = max(106 - sum(initial_bws), 0)
initial_bws[0] += leftover_bw

UEs_per_slice_string = ''
for x in UEs_per_slice:
    UEs_per_slice_string += f"{x} "

initial_bws_string = ''
for x in initial_bws:
    initial_bws_string += f"{x} "

# Traffic Parameters
openrtist_mean_on_time = 60
openrtist_mean_off_time = 600
iperf3_DL_mean_on_time = 120
iperf3_DL_mean_off_time = 240
iperf3_UL_mean_on_time = 120
iperf3_UL_mean_off_time = 240
