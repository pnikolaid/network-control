import os
import copy
from parameters import UEs_per_slice, slicenames
import time
import numpy as np

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

def parse_state_files_function():
    dir_path= os.path.dirname(os.getcwd())
    filenames = ['state_ul.txt', 'state_dl.txt']  # Replace with your file path
    filepaths = [os.path.join(dir_path, '5G-copies', filename) for filename in filenames]
    all_data = {}
    hops = ['UL', 'DL']
    for count, filepath in enumerate(filepaths):
        parsed_data = parse_file(filepath)
        slice_data = parse_per_slice(parsed_data)
        all_data[hops[count]] = slice_data
    print(all_data)
    return all_data

def extract_state_metrics(data):
    for hop in data.keys():
        for slice in data[hop]:
            array = np.array(data[hop][slice])
            old_bytes = sum(array[0][:,4])
            rates = []
            for frame_data in array:
                total_bytes = sum(frame_data[:, 4])
                rate_bytes = total_bytes - old_bytes
                old_bytes = total_bytes
                rates.append(rate_bytes)
            print(rates)

if __name__ == "__main__":
    t0 = time.time_ns()
    all_data = parse_state_files_function()
    extract_state_metrics(all_data)
    t1 = time.time_ns()


    print(f"Execution time: {(t1 - t0)/1e6} ms")
