import os
import numpy as np
import matplotlib.pyplot as plt
from parameters import iperf3_DL_mean_on_time, iperf3_DL_minimum_on_time, iperf3_DL_mean_off_time, iperf3_UL_mean_on_time, iperf3_UL_minimum_on_time, iperf3_UL_mean_off_time, openrtist_mean_off_time, openrtist_mean_on_time, openrtist_minimum_on_time, random_seed

np.random.seed(random_seed)

def create_UE_traffic(host_name, flow_type, N, T):

    # Distribution parameters
    if 'OpenRTiST' in flow_type:
        mean_on_time = openrtist_mean_on_time  
        mean_off_time = openrtist_mean_off_time
        minimum_on_time = openrtist_minimum_on_time   

    if 'iperf3_DL' in flow_type:
        mean_on_time = iperf3_DL_mean_on_time  
        mean_off_time = iperf3_DL_mean_off_time
        minimum_on_time = iperf3_DL_minimum_on_time   


    if 'iperf3_UL' in flow_type:
        mean_on_time = iperf3_UL_mean_on_time  
        mean_off_time = iperf3_UL_mean_off_time
        minimum_on_time = iperf3_UL_minimum_on_time   
        

    # From here on user, refers to a flow in the UE

    # Simulate on/off behavior for each user/flow
    user_status = np.zeros((N, T))

    for user in range(N):
        time = 0
        while time < T:

            on_time = np.random.exponential(mean_on_time)
            off_time = np.random.exponential(mean_off_time)
            
            on_time = max(on_time, minimum_on_time)

            time += int(off_time)
            
            end_time = min(int(time + on_time), T)
            if end_time <= T:
                user_status[user, int(time):int(end_time)] = 1
            
            time += end_time

    # Create directory if it doesn't exist
    parent_dir = os.path.dirname(os.getcwd())
    plots_dir = os.path.join(parent_dir, "plots")
    if not os.path.exists(plots_dir):
        os.makedirs(plots_dir)

    # Plotting
    plt.figure(figsize=(15, 6))

    # Plot user status
    for user in range(N):
        plt.step(range(T), user_status[user] + user * 1.5, where='post', label=f'Flow {user+1}')

    plt.xlabel('Time')
    plt.ylabel('Flow Status')
    plt.title(f'{host_name} -- {flow_type}')
    plt.yticks([])
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot as PDF in the plots folder
    plt.savefig(os.path.join(plots_dir, f'{host_name}_flow_status.pdf'), dpi=300)  # Adjust dpi as needed
    plt.close()

    # Calculate and plot total active users over time
    total_active_users = np.sum(user_status, axis=0)

    plt.figure(figsize=(15, 6))
    plt.step(range(T), total_active_users)
    plt.xlabel('Time')
    plt.ylabel('Number of Active Flows')
    plt.title(f'{host_name} -- {flow_type}')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot as PDF in the plots folder
    plt.savefig(os.path.join(plots_dir, f'{host_name}_total_active_flows.pdf'), dpi=300)  # Adjust dpi as needed
    plt.close()


    # Count frequency of each number of active users
    total_counts = len(total_active_users)
    active_users_counts = np.bincount(total_active_users.astype(int))

    # Print frequency of each number of active users
    for num_users, count in enumerate(active_users_counts):
        if count > 0:
            print(f"{num_users} active users occurred {count} times, i.e., {round(100*count/total_counts, 2)} fraction of time")
    
    source_times_durations = find_consecutive_ones(user_status)


    return user_status, source_times_durations, total_active_users

def find_consecutive_ones(array):
    new_list = []
    for arr in array:
        result = []
        start = None

        for i, num in enumerate(arr):
            if num == 1:
                if start is None:
                    start = i
            else:
                if start is not None:
                    result.append((start, i - start))
                    start = None

        # Check if the last sequence of 1s goes to the end of the list
        if start is not None:
            result.append((start, len(arr) - start))
        new_list.append(result)
    return new_list

if __name__ == '__main__':
    user_status,  source_times_durations = create_UE_traffic('kallepooc', 'OpenRTiST', 5, 1500)
    print(source_times_durations)
