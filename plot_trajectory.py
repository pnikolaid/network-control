from parameters import trajectories_folder
import os
import pickle
import glob

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

most_recent_pickle_filepath = find_most_recent_file(trajectories_folder)
print(most_recent_pickle_filepath)

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

print(data[-1])