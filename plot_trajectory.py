from parameters import trajectories_folder, slot_length, e2e_bound
import os
import pickle
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np

def check_e2e_qos(qos_results, slicename):
    if 'OpenRTiST' in slicename:
        qos_reward = 1
        for flow in qos_results:
            if 'mean' not in qos_results[flow]['E2E']:
                qos_reward = 0
                break
            if qos_results[flow]['E2E']['mean'] > e2e_bound:
                qos_reward = 0
                break
    return qos_reward


def find_most_recent_file(directory):
    try:
        # Get list of all files in the directory
        files = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        
        # Check if the list is empty
        if not files:
            return None
        
        # Get the most recent file based on modification time
        most_recent_file = max(files, key=os.path.getmtime)
        return most_recent_file
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_runtime_avg(some_list):
    some_list = np.array(some_list)
    some_list_cumsum = np.cumsum(some_list)
    some_list_avg = some_list_cumsum / np.arange(1, len(some_list) + 1)
    return some_list_avg

def average_per_unique_value(a, b):
    a = np.array(a)
    b = np.array(b)
    # Find unique values in b and their indices
    unique_b_values = np.unique(b)
    averages = {}
    values_per_unique_value = {}
    recent_averages = {}

    # Calculate the average of a based on the unique values in b
    for value in unique_b_values:
        mask = (b == value)
        average = np.mean(a[mask])
        averages[value] = average
        values_per_unique_value[value] = a[mask]
        recent_averages[value] = np.mean(a[mask][-30:])

    
    return averages, recent_averages


most_recent_pickle_filepath = find_most_recent_file(trajectories_folder)

# pickle_fileame = f"{experiment_identifier}.pkl"
# pickle_filepath = os.path.join(trajectories_folder, pickle_fileame)

pickle_filepath = most_recent_pickle_filepath

data = []
with open(pickle_filepath, 'rb') as f:
    try:
        while True:
            data.append(pickle.load(f))
    except EOFError:
        pass

# Extract the filename without the extension
file_name = os.path.basename(pickle_filepath)
experiment_identifier = os.path.splitext(file_name)[0] 

plot_results = {}
gpu_freqs = []
for slot_data in data:
    gpu_freq = slot_data['GPU_FREQ']
    for slicename in slot_data:
        if slicename == 'GPU_FREQ': continue

        # Initialize
        if slicename not in plot_results:
            plot_results[slicename] = {}
            plot_results[slicename]['active_flows'] = []
            plot_results[slicename]['ul_prbs'] = []
            plot_results[slicename]['dl_prbs'] = []
            plot_results[slicename]['gpu_freqs'] = []
            plot_results[slicename]['ul_mean_PRBs_states'] = []
            plot_results[slicename]['dl_mean_PRBs_states'] = []
            plot_results[slicename]['QoS'] = []

        slice_data = slot_data[slicename]
        qos = slice_data['QoS']
        plot_results[slicename]['active_flows'].append(len(slice_data['QoS']))
        plot_results[slicename]['ul_prbs'].append(slice_data['resources']['UL'])
        plot_results[slicename]['dl_prbs'].append(slice_data['resources']['DL'])
        plot_results[slicename]['ul_mean_PRBs_states'].append(slice_data['state']['UL']['mean PRB slice demand'])
        plot_results[slicename]['dl_mean_PRBs_states'].append(slice_data['state']['DL']['mean PRB slice demand'])
        plot_results[slicename]['gpu_freqs'].append(gpu_freq)
        plot_results[slicename]['QoS'].append(check_e2e_qos(qos, slicename))
        


time = list(range(len(data)))
time = [slot_length * t for t in time]

for slicename in plot_results:
    # Data for the plots
    active_flows = plot_results[slicename]['active_flows']
    dl_prbs = plot_results[slicename]['dl_prbs']
    dl_prbs_avg = get_runtime_avg(dl_prbs)

    ul_prbs = plot_results[slicename]['ul_prbs']
    ul_prbs_avg = get_runtime_avg(ul_prbs)

    gpu_freqs = plot_results[slicename]['gpu_freqs']
    gpu_freqs_avg = get_runtime_avg(gpu_freqs)

    e2e_qos = plot_results[slicename]['QoS']
    e2e_qos_avg = get_runtime_avg (e2e_qos)

    # Create a figure with two subplots
    fig, axs = plt.subplots(2, 2, figsize=(8, 6))
    ax1 = axs[0, 0]
    ax2 = axs[0, 1]
    ax3 = axs[1, 0]
    ax4 = axs[1, 1]

    # FIRST SUBPLOT for mean resource allocation plots
    # Create a y-axis for active flows
    ax1.plot(time, active_flows, color='b', label=f'flows')
    #ax1.set_title('Bandwidth over Time')
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Active Flows', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.yaxis.set_major_locator(MaxNLocator(integer=True))


    # Create a second y-axis for PRB allocations
    ax12 = ax1.twinx()
    ax12.plot(time, dl_prbs_avg, linestyle='--', color='r', label='DL PRBs')
    ax12.plot(time, ul_prbs_avg, color='r', label='UL PRBs')
    ax12.set_ylabel('Average PRBs', color='r')
    ax12.tick_params(axis='y', labelcolor='r')

    # Create a third y-axis for GPU frequencies
    ax13 = []
    #ax13 = ax1.twinx()
    #ax13.spines['right'].set_position(('outward', 60))  # Offset the third y-axis to the right
    #ax13.plot(time, gpu_freqs_avg, 'g', label='GPU Freq')
    #ax13.set_ylabel('GPU Freq', color='g')
    #ax13.tick_params(axis='y', labelcolor='g')

    # Combine handles and labels from both axes
    handles, labels = [], []
    for ax in [ax1, ax12, ax13]:
        if not ax: continue
        h, l = ax.get_legend_handles_labels()
        handles.extend(h)
        labels.extend(l)

    ax1.legend(handles, labels)

    # Calculate the average of a based on the unique values in b
    dl_prb_per_active_flows, dl_prb_recent_per_active_flows = average_per_unique_value(dl_prbs, active_flows)
    ul_prb_per_active_flows, ul_prb_recent_per_active_flows = average_per_unique_value(ul_prbs, active_flows)
    gpu_freqs_per_active_flows, gpu_freqs_recent_per_active_flows = average_per_unique_value(gpu_freqs, active_flows)
    qos_per_active_flows, qos_recent_per_active_flows = average_per_unique_value(e2e_qos, active_flows)

    print(dl_prb_recent_per_active_flows)
    print(ul_prb_recent_per_active_flows)
    print(qos_recent_per_active_flows)
    

    bar_width = 0.4  # Width of each bar

    # SECOND SUBPLOT FOR per state QoS
    y_qos = [int(100*v) for v in qos_per_active_flows.values()]
    bars = ax2.bar(qos_per_active_flows.keys(), y_qos, bar_width)

    barss = ax2.bar(list(qos_per_active_flows.keys())[-1] +  1, int(100*e2e_qos_avg[-1]), bar_width)

    # Annotate bars with their values
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, height/2, f'{height}%', ha='center', va='bottom')
    height = barss[0].get_height()
    ax2.text(barss[0].get_x() + barss[0].get_width() / 2, height/2, f'{height}%', ha='center', va='bottom')

    # Add labels and title
    ax2.set_xlabel('Active Flows')
    ax2.set_ylabel('QoS Satisfied')
    #ax2.set_title('QoS')
    ax2_ticks = list(qos_per_active_flows.keys())
    ax2_ticks.append(ax2_ticks[-1] +  1)                 
    ax2.set_xticks(ax2_ticks)
    ax2_ticklabels = list(qos_per_active_flows.keys())
    ax2_ticklabels.append('overall')
    ax2.set_xticklabels(ax2_ticklabels)
    ax2.legend()
    
    # THIRD SUBPLOT for per state BW

    # X positions for the groups of bars
    x = np.arange(len(ul_prb_per_active_flows))

    # Plot bars for Category 1
    bars1 = ax3.bar(x - bar_width/2, ul_prb_per_active_flows.values(), bar_width, label='uplink')

    # Plot bars for Category 2
    bars2 = ax3.bar(x + bar_width/2, dl_prb_per_active_flows.values(), bar_width, label='downlink')

    # Annotate bars with their values
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width() / 2, height/2, f'{int(height)}', ha='center', va='bottom')

    # Add labels and title
    ax3.set_xlabel('Active Flows')
    ax3.set_ylabel('Average PRBs')
    #ax3.set_title('Bandwidth Allocations')
    ax3.set_xticks(x)
    ax3.set_xticklabels(ul_prb_per_active_flows.keys())
    ax3.legend()

    # FOURTH SUBPLOT FOR per state GPU
    y_gpu = [int(v) for v in gpu_freqs_per_active_flows.values()]
    bars = ax4.bar(gpu_freqs_per_active_flows.keys(), y_gpu, bar_width)

    # Annotate bars with their values
    for bar in bars:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width() / 2, height/2, f'{height}', ha='center', va='bottom')

    # Add labels and title
    ax4.set_xlabel('Active Flows')
    ax4.set_ylabel('GPU Freq (MHz)')
    #ax4.set_title('GPU')
    ax4_ticks = list(gpu_freqs_per_active_flows.keys())
    ax4.set_xticks(ax4_ticks)
    ax4_ticklabels = list(gpu_freqs_per_active_flows.keys())
    ax4.set_xticklabels(ax4_ticklabels)
    ax4.legend()

    # Add a title and display the plot
    plt.suptitle(f'{slicename} Results')
    fig.tight_layout()  # Adjust layout to prevent overlap

    # Save the figure
    plt.savefig(f'{slicename}.pdf')
