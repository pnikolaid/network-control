import os
import numpy as np
import matplotlib.pyplot as plt
from parameters import iperf3_DL_mean_on_time, iperf3_DL_mean_off_time, iperf3_UL_mean_on_time, iperf3_UL_mean_off_time, openrtist_mean_off_time, openrtist_mean_on_time

def create_UE_traffic(host_name, flow_type, N, T):

    # Distribution parameters
    if 'OpenRTiST' in flow_type:
        mean_on_time = openrtist_mean_on_time  
        mean_off_time = openrtist_mean_off_time   

    if 'iperf3_DL' in flow_type:
        mean_on_time = iperf3_DL_mean_on_time  
        mean_off_time = iperf3_DL_mean_off_time

    if 'iperf3_UL' in flow_type:
        mean_on_time = iperf3_UL_mean_on_time  
        mean_off_time = iperf3_UL_mean_off_time        

    # From here on user, refers to a flow in the UE

    # Simulate on/off behavior for each user/flow
    user_status = np.zeros((N, T))

    for user in range(N):
        time = 0
        while time < T:

            if 'OpenRTiST' in flow_type:
                on_time = np.random.exponential(mean_on_time)
                off_time = np.random.exponential(mean_off_time)

            if 'iperf3' in flow_type:
                on_time = np.random.exponential(mean_on_time)
                off_time = np.random.exponential(mean_off_time)

            
            if time + int(on_time) < T:
                user_status[user, int(time):int(time + on_time)] = 1
            
            time += int(on_time + off_time)

    # Create directory if it doesn't exist
    parent_dir = os.path.dirname(os.getcwd())
    plots_dir = os.path.join(parent_dir, "plots")
    print(plots_dir)
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

    # Save the plot as JPG in the plots folder
    plt.savefig(os.path.join(plots_dir, f'{host_name}_flow_status.pdf'), dpi=300)  # Adjust dpi as needed
    plt.close()

    # Calculate and plot total active users over time
    total_active_users = np.sum(user_status, axis=0)

    plt.figure(figsize=(15, 6))
    plt.plot(range(T), total_active_users, marker='o')
    plt.xlabel('Time')
    plt.ylabel('Number of Active Flows')
    plt.title(f'{host_name} -- {flow_type}')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Save the plot as JPG in the plots folder
    plt.savefig(os.path.join(plots_dir, f'{host_name}_total_active_flows.pdf'), dpi=300)  # Adjust dpi as needed
    plt.close()


    # Count frequency of each number of active users
    total_counts = len(total_active_users)
    active_users_counts = np.bincount(total_active_users.astype(int))

    # Print frequency of each number of active users
    for num_users, count in enumerate(active_users_counts):
        if count > 0:
            print(f"{num_users} active users occurred {count} times, i.e., {round(100*count/total_counts, 2)} fraction of time")
    
    print(user_status)

    return user_status

if __name__ == '__main__':
    create_UE_traffic('kallepooc', 'OpenRTiST', 2, 1500)

