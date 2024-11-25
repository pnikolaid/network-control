# network-control

Python scripts that automatically adapt the network resources (PRBs in UL/DL and GPU freq in the EDGE)

traffic_generator.py: the main python script that creates traffic scenarios and invokes the network automation code script called network_control.py

parameters.py: contain parameters for the configuration of the traffic and network control parameters

Folder "scenario_parameters" contains the parameter files of five scenarios, copy and paste such a file in the main directory and then rename it to "parameters.py"

Installation
1) Follow the testbed setup guide in https://github.com/KTH-EXPECA/openairinterface5g-docs/blob/main/docs/quectel/start.md

2) Clone the bash scripts in https://github.com/pnikolaid/network-bash-scripts in the same folder where the customized Open Air Interface 5G repository of step 1

3) Clone this repository in the same folder
