import os
import copy
from parameters import UEs_per_slice, slicenames, log_5G_state_period_in_ms, symbols_per_subframe, TDD_slots_ratio, iperf3_UL_rate, iperf3_DL_rate, openrtist_rate_DL, openrtist_rate_UL
import time
import numpy as np
from collections import defaultdict

# Define the dictionary mapping MCS index to spectral efficiency according to Table 5.1.3.1-1 of 38.214 in nr_mac_common.c (it is the same both in UL and DL)

mcs_to_spectral_efficiency = {
    0: 0.2344, 1: 0.3066, 2: 0.3770, 3: 0.4902, 4: 0.6016,
    5: 0.7402, 6: 0.8770, 7: 1.0273, 8: 1.1758, 9: 1.3262,
    10: 1.3281, 11: 1.4766, 12: 1.6953, 13: 1.9141, 14: 2.1602,
    15: 2.4063, 16: 2.5703, 17: 2.5664, 18: 2.7305, 19: 3.0293,
    20: 3.3223, 21: 3.6094, 22: 3.9023, 23: 4.2129, 24: 4.5234,
    25: 4.8164, 26: 5.1152, 27: 5.3320, 28: 5.5547,
    29: None, 30: None, 31: None  # Reserved entries
}

def parse_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Split the content by 'Frame'
    frames = content.strip().split('Frame')
    
    data = []
    
    for frame in frames:
        if frame.strip() == "":
            continue
        
        lines = frame.strip().split('\n')
        # frame_number = int(lines[0].strip())
        
        rows = []
        for line in lines[2:]:
            if line.strip() == "":
                continue
            values = list(map(int, line.split()))
            rows.append(values)
        
        data.append(rows)
    
    return data  # [[[UID, DTX, MCS, MAC, RLC], [UID, DTX, MCS, MAC RLC], ...]...]

control_overheard_in_resources = {'UL': 0.08, 'DL': 0.14}

def uid_to_sliceid(uid):
    sliceid = 0
    max_uid = -1
    for sliceid, num_ues in enumerate(UEs_per_slice):
        max_uid += num_ues 
        if uid <= max_uid:
            break
    
    return sliceid


def parse_per_slice(parsed_data):
    slices_data = {}
    for slicename in slicenames:
        slices_data[slicename] = []

    for count, frame in enumerate(parsed_data):
        ues_remaining = copy.deepcopy(UEs_per_slice)
        for slicename in slicenames:
            slices_data[slicename].append([])
        for row in frame:
            uid = row[0]
            sliceid = uid_to_sliceid(uid)
            if ues_remaining[sliceid] != 0:
                slicename = slicenames[sliceid]
                slices_data[slicename][count].append(row)
                ues_remaining[sliceid] -= 1
    
    return slices_data

def preprocess_state_files():
    dir_path= os.path.dirname(os.getcwd())
    filenames = ['state_ul.txt', 'state_dl.txt']  # Replace with your file path
    filepaths = [os.path.join(dir_path, '5G-copies', filename) for filename in filenames]
    all_data = {}
    hops = ['UL', 'DL']
    for count, filepath in enumerate(filepaths):
        parsed_data = parse_file(filepath)
        slice_data = parse_per_slice(parsed_data)
        all_data[hops[count]] = slice_data
    #print(all_data)
    return all_data

def extract_state_metrics(data):
    state_metrics = {}
    for hop in data.keys():
        state_metrics[hop] = {}

        for slice in data[hop]:
            state_metrics[hop][slice] = {}

            array = np.array(data[hop][slice])
            old_ue_bytes = array[0][:, 4]
            old_mcss = array[0][:, 2]
            old_spectral_efficiency = np.array([mcs_to_spectral_efficiency[m] for m in old_mcss])

            rates_over_slot = [] # slot refers to the control slot (in the order of seconds)
            PRB_factor_over_slot = [] 
            queue_bytes_over_slot = []
            slice_PRB_demand_per_flow_over_time = []

            if "OpenRTiST" in slice:
                if "DL" == hop:
                    arrival_flow_metrics = np.array(openrtist_rate_DL)
                if "UL" == hop:
                    arrival_flow_metrics = np.array(openrtist_rate_UL)
            if "iperf3" in slice:
                if "DL" == hop:
                    arrival_flow_metrics = np.array([float(iperf3_DL_rate[:-1]), 0, float(iperf3_DL_rate[:-1])])
                if "UL" == hop:
                    arrival_flow_metrics = np.array([float(iperf3_UL_rate[:-1]), 0, float(iperf3_UL_rate[:-1])])
            
            flow_bits_per_frame = arrival_flow_metrics[0] * 1e4

            for frame_data in array[1:,]:
                
                ue_bytes = frame_data[:, 4]
                rate_bytes = ue_bytes - old_ue_bytes
                old_ue_bytes = ue_bytes
                total_rate = (sum(rate_bytes) * 8) / (log_5G_state_period_in_ms * 1000) # in Mbps

                bits_per_frame = 10 * 8 * rate_bytes/log_5G_state_period_in_ms # on average bits arriving every frame


                # PRBs needed to match the arrival rate =  (some system constants that depends on 5G configuration)* PRB_factor (for each UE)
                data_resources_perc = 1 - control_overheard_in_resources[hop] 
                slots_perc = TDD_slots_ratio[hop]
                PRB_factors = bits_per_frame / (old_spectral_efficiency * 12 * symbols_per_subframe * 10 * data_resources_perc * slots_perc) # based on TS 38.306 Sec. 4.1, we multiply by 28 since there are 28 symbols in 1 ms when SCS = 30 kHz
                total_PRB_factor = sum(PRB_factors)  # total PRBs needed to match the slice's arrival rate = (the same unknown constant)*total_PRB_factor

                slice_PRB_demand_per_flow = []
                for sf in old_spectral_efficiency:
                    ue_flow_PRB_demand = flow_bits_per_frame / (sf * 12 * symbols_per_subframe * 10 * data_resources_perc * slots_perc) # based on TS 38.306 Sec. 4.1, we multiply by 28 since there are 28 symbols in 1 ms when SCS = 30 kHz
                    slice_PRB_demand_per_flow.append(ue_flow_PRB_demand)
                slice_PRB_demand_per_flow = np.array(slice_PRB_demand_per_flow)

                mcss = frame_data[:, 2]
                spectral_efficiency = np.array([mcs_to_spectral_efficiency[m] for m in mcss])
                old_spectral_efficiency = spectral_efficiency


                queue_bytes = frame_data[:, 3]
                total_queue_bytes = sum(queue_bytes)



                rates_over_slot.append(total_rate)
                PRB_factor_over_slot.append(total_PRB_factor)
                queue_bytes_over_slot.append(total_queue_bytes)
                slice_PRB_demand_per_flow_over_time.append(slice_PRB_demand_per_flow)

            current_queue = total_queue_bytes
            rate_metrics = [np.mean(rates_over_slot), np.std(rates_over_slot), np.max(rates_over_slot)]
            PRB_factor_metrics = [np.mean(PRB_factor_over_slot), np.std(PRB_factor_over_slot), np.max(PRB_factor_over_slot)]
            queue_metrics = [np.mean(queue_bytes_over_slot), np.std(queue_bytes_over_slot), np.max(queue_bytes_over_slot), current_queue]

            slice_PRB_demand_per_flow_over_time = np.array(slice_PRB_demand_per_flow_over_time)
            state_metrics[hop][slice]["PRB demand per flow metrics"] = [list(np.mean(slice_PRB_demand_per_flow_over_time, axis = 0)), list(np.std(slice_PRB_demand_per_flow_over_time, axis = 0)), list(np.max(slice_PRB_demand_per_flow_over_time, axis = 0))]

            #print(rate_metrics)
            #print(PRB_factor_metrics)
            #print(queue_metrics)
            state_metrics[hop][slice]["arrival rate metrics"] = rate_metrics # mean, std, max
            state_metrics[hop][slice]["PRB demand metrics"] = PRB_factor_metrics # mean, std, max
            state_metrics[hop][slice]["queue metrics"] = queue_metrics #nean, std, max, current
    # print(state_metrics)

    # Iterate nesting order of dictionary
    new_state_metrics = {}
    for hop, slices in state_metrics.items():
        for slice_key, value in slices.items():
            if slice_key not in new_state_metrics:
                new_state_metrics[slice_key] = {}
            new_state_metrics[slice_key][hop] = value

    return new_state_metrics

def parse_state_files_function():
    all_data = preprocess_state_files()
    new_state_metrics = extract_state_metrics(all_data)
    return new_state_metrics


if __name__ == "__main__":
    t0 = time.time_ns()
    state_metrics = parse_state_files_function()
    print(state_metrics)
    t1 = time.time_ns()


    print(f"Execution time: {(t1 - t0)/1e6} ms")
