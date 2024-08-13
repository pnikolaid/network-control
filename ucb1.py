import numpy as np
from collections import defaultdict
import time


class vUCB1:
    def __init__(self, actions, action_cost_parameter, arm_correlations=True):
        self.arms = actions
        self.num_arms = len(self.arms)
        self.iterations = 0
        self.action_cost_parameter = action_cost_parameter

        # Determine if arm correlations are considered
        self.arm_correlations = arm_correlations

        # Action costs
        if type(action_cost_parameter) is list:
            max_action_list = list(np.amax(np.array(actions), axis=0))
            min_action_list = list(np.amin(np.array(actions), axis=0))

            self.max_action_cost = sum([x*y for x,y in zip(max_action_list, action_cost_parameter)])
            self.min_action_cost = sum([x*y for x,y in zip(min_action_list, action_cost_parameter)])
        else:
            action_costs = [v*action_cost_parameter for v in actions]
            self.max_action_cost = max(action_costs)
            self.min_action_cost = min(action_costs)
        
        self.cost_of_qos = (self.max_action_cost - self.min_action_cost)/ 0.2

        # convert to dictionaries
        self.counts_dic = defaultdict(int)
        self.avg_rewards_dic = defaultdict(int)

        # When correlations are considered, self.counts[a] is not the number of times that arm 'a' is selected
        self.times_selected_dic = defaultdict(int)

        self.first_time = True

    def compute_normalized_reward(self, action, qos_reward):    
        
        if type(action) is list:
            total_action_cost =  sum([x*y for x,y in zip(action, self.action_cost_parameter)])
        else:
            total_action_cost = action * self.action_cost_parameter
        round_cost = total_action_cost + (1 - qos_reward) * self.cost_of_qos
        round_reward = -round_cost
        max_cost = self.max_action_cost + self.cost_of_qos
        min_cost = self.min_action_cost

        min_reward = -max_cost
        max_reward = -min_cost
        round_reward = (round_reward - min_reward) / (max_reward - min_reward)
        
        return round_reward

    def select_arm(self):
        if self.first_time:
            middle = int(self.num_arms/2)
            selected_arm = self.arms[middle]
            self.first_time = False
            return selected_arm
        
        ucb_indices_dic = defaultdict(int)
        
        for arm in self.arms:

            if self.counts_dic[arm] == 0:
                selected_arm = arm
                #self.print_debug_info(ucb_indices_dic, selected_arm)
                self.times_selected_dic[selected_arm] += 1
                return selected_arm

            exploitation = self.avg_rewards_dic[arm]
            exploration = np.sqrt((2 * np.log(self.iterations) / self.counts_dic[arm]))
            ucb_indices_dic[arm] = exploitation + exploration

        # select arm with highest ucb_index
        selected_arm = max(ucb_indices_dic, key=ucb_indices_dic.get)

        # self.print_debug_info(ucb_indices_dic, selected_arm)
        self.times_selected_dic[selected_arm] += 1
        return selected_arm

    def print_debug_info(self, ucb_values_dic, selected_arm):
        print(f"Counts: {self.counts_dic}")
        print(f"Average Rewards: {self.avg_rewards_dic}")
        print(f"UCB Values: {ucb_values_dic}")
        print(f"Selected Arm: {selected_arm}")

    def single_arm_update(self, arm, reward):
        self.counts_dic[arm] += 1
        new_counts = self.counts_dic[arm]
        old_counts = new_counts - 1

        old_avg_reward = self.avg_rewards_dic[arm]
        new_avg_reward = 1 / float(new_counts) * (old_avg_reward * old_counts + reward)
        self.avg_rewards_dic[arm] = new_avg_reward

    def update(self, selected_arm, QoS_reward):

        # The selected arm is always updated regardless of correlations
        sel_reward = self.compute_normalized_reward(selected_arm, QoS_reward)
        self.single_arm_update(selected_arm, sel_reward)

        # if arm correlations are considered, also update correlated arms
        if self.arm_correlations:

            # Find arms that are elementise smaller or larger than the selected arm
            selected_arm_np = np.array(selected_arm)
            larger_arms = []
            smaller_arms = []
            for arm in self.arms:
                if arm == selected_arm: continue
                arm_np = np.array(arm)
                diff = arm_np - selected_arm_np
                if (diff >= 0).all():
                    larger_arms.append(arm)
                if (diff <= 0).all():
                    smaller_arms.append(arm)
            
            # If we did not meet the SLA, smaller arms/bandwidths would also fail
            if QoS_reward == 0:
                for arm in smaller_arms:
                    reward = self.compute_normalized_reward(arm, 0)
                    self.single_arm_update(arm, reward)

            # If we met the SLA, larger arms/bandwidths would also succeed
            if QoS_reward == 1:
                for arm in larger_arms:
                    reward = self.compute_normalized_reward(arm, 1)
                    self.single_arm_update(arm, reward)

        # Algorithm just finished an iteration
        self.iterations += 1
        return sel_reward


# ------------------------------------------------- Main starts here ---------------------------------------------------
if __name__ == "__main__":

    # Set number of arms and their arm dependent delay to simulate rewards later on
    NUM_ARMS = 1000
    arms = list(range(NUM_ARMS))
    arm_dependent_delay = list(reversed(range(NUM_ARMS)))  # larger arms/bandwidths achieve smaller delay
    desired_delay_upper_bound = 100

    arm_cost_parameter = 1

    # Create an instance of UCB1 with the specified number of arms and specify if arm correlations are considered
    ucb = vUCB1(arms, arm_cost_parameter, True)

    num_rounds = 1000
    total_reward = 0
    start_time = time.time()
    for i in range(num_rounds):
        # Choose an arm
        arm_selected = ucb.select_arm()

        # Simulate a reward for the selected arm
        noise = np.random.normal(0, 10)
        arm_selected_index = arms.index(arm_selected)
        delay = arm_dependent_delay[arm_selected_index] + noise
        if delay <= desired_delay_upper_bound:
            QoS_REWARD = 1
        else:
            QoS_REWARD = 0

        # Update the UCB1 model with the selected arm and QoS reward and obtain normalized round reward
        reward = ucb.update(arm_selected, QoS_REWARD)
        total_reward += reward
        print(f"Arm {arm_selected} QoS_Reward {QoS_REWARD} Reward {reward}")
    
    end_time = time.time()
    average_loop_time = (end_time-start_time)/num_rounds
    print(f"The average loop time is: {int(average_loop_time*1000)} ms")
    print(f"Total reward is: {total_reward}")
    #print(ucb.times_selected_dic)