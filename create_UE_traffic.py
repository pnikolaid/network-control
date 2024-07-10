import os
import numpy as np
import matplotlib.pyplot as plt

# Parameters
N = 5  # Number of users
T = 3600  # Total time units to simulate

# Exponential distribution parameters
mean_on_time = 60  # Mean on time
mean_off_time = 600   # Mean off time

# Simulate on/off behavior for each user
user_status = np.zeros((N, T))

for user in range(N):
    time = 0
    while time < T:
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
    plt.step(range(T), user_status[user] + user * 1.5, where='post', label=f'User {user+1}')

plt.xlabel('Time')
plt.ylabel('User Status')
plt.title('On/Off Status for Each User')
plt.yticks([])
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save the plot as JPG in the plots folder
plt.savefig(os.path.join(plots_dir, 'user_status.jpg'), dpi=300)  # Adjust dpi as needed
plt.close()

# Calculate and plot total active users over time
total_active_users = np.sum(user_status, axis=0)

plt.figure(figsize=(15, 6))
plt.plot(range(T), total_active_users, label='Total Active Users', marker='o')
plt.xlabel('Time')
plt.ylabel('Number of Active Users')
plt.title('Total Number of Active Users Over Time')
plt.legend()
plt.grid(True)
plt.tight_layout()

# Save the plot as JPG in the plots folder
plt.savefig(os.path.join(plots_dir, 'total_active_users.jpg'), dpi=300)  # Adjust dpi as needed
plt.close()


# Count frequency of each number of active users
total_counts = len(total_active_users)
print(total_counts)
active_users_counts = np.bincount(total_active_users.astype(int))

# Print frequency of each number of active users
print("Frequency of Number of Active Users:")
for num_users, count in enumerate(active_users_counts):
    if count > 0:
        print(f"{num_users} active users occurred {count} times which is {round(100*count/total_counts, 2)} fraction of time")



print(f"Plots saved in the '{plots_dir}' folder: user_status.jpg and total_active_users.jpg")
