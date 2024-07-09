import os
import math
import time
from collections import defaultdict
import numpy as np
import concurrent.futures
import re

def list_files_in_directory(folder):
    """Return a list of filenames in the given directory."""
    try:
        names = os.listdir(folder)
        return names
    except Exception as e:
        print(f"Error: {e}")
        return []


def parse_timestamp_file(file_directory, file_name):
    if "sent" in file_name and "client" in file_name:
        order = 0
    elif "recv" in file_name and "server" in file_name:
        order = 1
    elif "sent" in file_name and "server" in file_name:
        order = 2
    elif "recv" in file_name and "client" in file_name:
        order = 3
    else:
        order = 3

    # hostname = file_name.split('_')[0]
    filepath = os.path.join(file_directory, file_name)
    with open(filepath, 'r') as file:
        for line in file:
            parts = line.strip().split()
            port = int(parts[0])
            seq_num = int(parts[1])
            timestamp = int(parts[2])
            timestamps[port][seq_num][order] = timestamp
    return timestamps


def print_timestamp_dict():
        for port in timestamps:
            print(f"\t{port}:\n")
            for seq_num in timestamps[port]:
                print(f"\t{seq_num}:{timestamps[port][seq_num]}")

def compute_delays(timestamps_dict):
    errors  = 0
    frames = 0
    delays_ul = []
    delays_edge = []
    delays_dl = []
    delays_e2e = []
    for port in timestamps_dict:
        for seq_num in timestamps_dict[port]:
            times = timestamps_dict[port][seq_num]
            frames += 1

            if -1 in times:
                print()
                print("Ignoring frame that does not have all timestamps...")
                print(f"Timestamps: {times}")
                print()
                errors += 1
                continue

            delay_ul = (times[1] - times[0]) / 1e6
            delay_edge = (times[2] - times[1]) / 1e6
            delay_dl = (times[3] - times[2]) / 1e6
            delay_e2e = (times[3] - times[0]) / 1e6

            if delay_ul < 0 or delay_edge < 0 or delay_dl < 0 or delay_e2e <0:
                print()
                print("Ignoring frame that has negative delays...")
                print(f"timestamps: {times}")
                print(f"Delays: {[delay_ul, delay_edge, delay_dl, delay_e2e]}")
                print()
                errors += 1
                continue

            delays_ul.append(delay_ul)
            delays_edge.append(delay_edge)
            delays_dl.append(delay_dl)
            delays_e2e.append(delay_e2e)

    error_perc = round(100* errors/frames, 2)
    print(f"Percentage of erroneous frames: {error_perc}%")
    return delays_ul, delays_edge, delays_dl, delays_e2e

def compute_statistics(delays):
    """Calculate and return statistical measures from the list of delays."""
    n = len(delays)
    mean_delay = sum(delays) / n
    max_delay = max(delays)
    min_delay = min(delays)
    variance = sum((x - mean_delay) ** 2 for x in delays) / n
    std_deviation = math.sqrt(variance)
    percentage = 90
    percentile = np.percentile(delays, percentage, method='inverted_cdf') 
    stats = {
        'mean': round(mean_delay, 2),
        'max': round(max_delay, 2),
        'min': round(min_delay, 2),
        'std': round(std_deviation, 2),
        str(percentage) + '%' : round(percentile, 2)
    }
    return stats

def print_stats_dict(stats):
        print("\n")
        print("OpenRTiST Frame Delays (ms):\n")
        stat_names = list(stats["DL"].keys())
        for name in stat_names:
            print(f"{'':<6}{name:<4}", end="")
        print("\n")

        for hop_name in stats:
            print(f"{hop_name:<6}", end="")
            for stat in stats[hop_name]:
                entry = stats[hop_name][stat]
                print(f"{entry:<10}", end="")
            print("\n")
        print("\n")

def parse_iperf_files(folder, filename):
    filepath = os.path.join(folder, filename)
    dl_flag = False
    if 'dl' in filename:
        results = iperf_dl
        dl_flag = True
    else:
        results = iperf_ul
        match = re.search(r'_([^_]+)\.txt$', filename)
        if match:
            ul_port = match.group(1)
        else:
            ul_port = 5201
        
    with open(filepath, 'r') as file:
        for line in file:
            # Split the line into components based on whitespace
            parts = line.split()

            if dl_flag:
                if len(parts) >= 8 and parts[0].endswith(':'):
                    port = parts[0][:-1]
                    bitrate = parts[7]

                    # Check if it's a valid numeric value before saving
                    try:
                        bitrate_value = float(bitrate)
                    except ValueError:
                        continue

                    # Add the value to the the right iperf dictionary
                    if port not in results:
                        results[port] = []
                    results[port].append(bitrate_value)
            else:
                if len(parts) >= 8:
                    port = ul_port
                    bitrate = parts[6]

                    # Check if it's a valid numeric value before saving
                    try:
                        bitrate_value = float(bitrate)
                    except ValueError:
                        continue

                    # Add the value to the the right iperf dictionary
                    if port not in results:
                        results[port] = []
                    results[port].append(bitrate_value)

def compute_iperf_stats(stats):
    results = {}
    for key in stats:
        results[key] = round(sum(stats[key]) / len(stats[key]), 2)

    return results

def parse_file(file_name):
    if "feanor" in file_name or "finarfin" in file_name:
        print(f"Parsing {file_name}")
        if "timestamps" in file_name:
            parse_timestamp_file(directory, file_name)
        elif "iperf3" in file_name:
            parse_iperf_files(directory, file_name)

def perform_in_parallel(function, f_inputs):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(function, f_input): f_input for f_input in f_inputs}
        for future in concurrent.futures.as_completed(futures):
            input_value = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"Input {input_value} generated an exception: {exc}")



# Create a dictionary to store timestamps: port -> sequence number -> timestamp x 4 (flows are differentiated based on the port that each OpenRTiST server uses)
directory = '/home/wlab/panos/algo/QoS_files'
filenames = list_files_in_directory(directory)


timestamps = defaultdict(lambda: defaultdict(lambda: [-1, -1, -1, -1]))
iperf_dl = {}
iperf_ul = {}

show_timestamps = False
show_stats = True

show_iperf_dict = False
show_iperf_results = True

# Run the main function
if __name__ == "__main__":

    start_time = time.time_ns()


    # Parse files to fill up timestamps and iperf dictionaries
    """
    for name in filenames:
        if "feanor" in name or "finarfin" in name:
            print(f"Parsing {name}")
            if "timestamps" in name:
                parse_timestamp_file(directory, name)
            elif "iperf3" in name:
                parse_iperf_files(directory, name)
    """
    
    perform_in_parallel(parse_file, filenames)

    # Compute timestamp statistics
    if show_timestamps:
        print_timestamp_dict(timestamps)

    delay_hops = [[], [], [], []]
    name_hops = ["UL", "EDGE", "DL", "E2E"]
    delay_hops[0], delay_hops[1], delay_hops[2], delay_hops[3] = compute_delays(timestamps)

    print("")

    all_stats = {}
    for k, vector in enumerate(delay_hops):
        statistics = compute_statistics(vector)
        all_stats[name_hops[k]] = statistics


    if show_stats:
        print_stats_dict(all_stats)


    # Compute iperf3 statistics
    if show_iperf_dict:
        print("Iperf3 DL bitrates (Mbps):")
        for key in iperf_dl:
            print(f'{key}: {iperf_dl[key]}')
        print()

        print("Iperf3 UL bitrates (Mbps):")
        for key in iperf_ul:
            print(f'{key}: {iperf_ul[key]}')
        print()
    
    iperf_dl_results = compute_iperf_stats(iperf_dl)
    iperf_ul_results = compute_iperf_stats(iperf_ul)
        
    if show_iperf_results:
        print("Iperf3 DL mean bitrate (Mbps):")
        for key in iperf_dl_results:
            print(f'{key}: {iperf_dl_results[key]}')
        print()
        
        print("Iperf3 UL mean bitrate (Mbps):")
        for key in iperf_ul_results:
            print(f'{key}: {iperf_ul_results[key]}')
        print()
    
            

    end_time = time.time_ns()
    print(f"Execution time: {(end_time - start_time)/1e6} ms")
