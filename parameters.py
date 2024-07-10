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

# All hosts
remote_path = '/tmp'  # contains filepath to QoS files in each host
local_path = '../QoS_files' # contains filepath to QoS files in server

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

experiment_folder = 'panos'   # folder that contains all required repositories (should be the same for all hosts)
hosts = copy.deepcopy(all_hosts)


experiment_setup = {'server': [('finarfin',)], 'OpenRTiST': [('feanor', 2)], 'iperf3': [] }  # tuple format: (hostname, maximum number of flows), cannot have a host used by two slices
keep_only_experiment_hosts(experiment_setup)

UEs_per_slice = [len(experiment_setup[key]) for key in experiment_setup.keys() if key != 'server']  # each host has one UE thus num of UEs = num of hosts
experiment_duration = 3600 # in seconds