import paramiko
from scp import SCPClient
import os
import concurrent.futures
import time

from parameters import hosts, QoS_folder

def create_ssh_client(hostname, port, username, password):
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, port=port, username=username, password=password)
    return client

def get_matching_files(ssh_client, remote_path, patterns):
    command = f'ls {remote_path}'
    stdin, stdout, stderr = ssh_client.exec_command(command)
    files = stdout.read().decode().split()
    matching_files = [file for file in files if any(file.startswith(pattern) for pattern in patterns)]
    return matching_files

def download_files(ssh_client, remote_path, local_path, filenames, hostname):
    os.makedirs(local_path, exist_ok=True)
    with SCPClient(ssh_client.get_transport()) as scp:
        for filename in filenames:
            remote_file = os.path.join(remote_path, filename)
            filename = hostname + "_" + filename
            local_file = os.path.join(local_path, filename)
            # print(f"Downloading {remote_file} to {local_file}")
            scp.get(remote_file, local_file)

def download_files_scp(scp_client, remote_path, local_path, filenames, hostname):
    os.makedirs(local_path, exist_ok=True)
    for filename in filenames:
        remote_file = os.path.join(remote_path, filename)
        filename = hostname + "_" + filename
        local_file = os.path.join(local_path, filename)
        # print(f"Downloading {remote_file} to {local_file}")
        scp_client.get(remote_file, local_file)

def process_host(host_name):
    host = hosts[host_name]
    ssh_client = create_ssh_client(host["IP"], host["port"], host["username"], host["password"])
    patterns = ['sent_timestamp', 'recv_timestamp', 'iperf3_dl', 'iperf3_ul']
    filenames = get_matching_files(ssh_client, host["remote_path"], patterns)
    download_files(ssh_client, host["remote_path"], QoS_folder, filenames, host_name)
    ssh_client.close()

def process_host_scp_created(host_info):
    host_name = host_info[0]
    ssh_client = host_info[1]
    remote_path = host_info[2]
    scp_client = host_info[3]
    patterns = ['sent_timestamp', 'recv_timestamp', 'iperf3_dl', 'iperf3_ul']
    filenames = get_matching_files(ssh_client, remote_path, patterns)
    download_files_scp(scp_client, remote_path, QoS_folder, filenames, host_name)

def perform_in_parallel(function, f_inputs):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(function, f_input): f_input for f_input in f_inputs}
        for future in concurrent.futures.as_completed(futures):
            input_value = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"Input {input_value} generated an exception: {exc}")

def main():
    perform_in_parallel(process_host, hosts)
   
if __name__ == '__main__':

    t0 =  time.time_ns()
    main()
    t1 = time.time_ns()
    print(f"Execution time: {(t1 - t0)/1e6} ms")
