#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import numpy as np
import gym
from gym import spaces

class F1RaceEnv(gym.Env):
    def __init__(self, race_data):
        super(F1RaceEnv, self).__init__()

        self.race_data = race_data

        # Number of drivers based on lap time matrix
        self.num_drivers = self.race_data['lap_times'].shape[1]

        # State space:
        # [Lap, Position, Gap to Leader, Gap to Car Ahead, Tyre Type, Tyre Age, Pit Stop History]
        self.state_shape = (self.num_drivers, 7)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=self.state_shape, dtype=np.float32
        )

        # Action Space:
        # Pace Strategy (3) x Pit Decision (2) x Tire Choice (3) = 18 discrete actions
        self.action_space = spaces.Discrete(18)

        # Internal state tracking
        self.current_lap = 0
        self.state = None

    def reset(self):
        """
        Reset the environment at the start of the race.
        """
        self.current_lap = 1

        # Get lap data for the first lap
        lap_times = self.race_data['lap_times'].iloc[self.current_lap - 1].values
        gaps_to_leader = self.race_data['gaps_to_leader'].iloc[self.current_lap - 1].values
        gaps_to_car_ahead = self.race_data['gaps_to_car_ahead'].iloc[self.current_lap - 1].values

        # Initialize state tensor (positions based on lap times)
        self.state = np.zeros(self.state_shape)

        for i in range(self.num_drivers):
            self.state[i] = [
                self.current_lap,                  # Lap number
                i + 1,                             # Track position
                gaps_to_leader[i],                 # Gap to leader
                gaps_to_car_ahead[i],              # Gap to car ahead
                0,                                 # Tyre Type (Soft = 0, Medium = 1, Hard = 2)
                0,                                 # Tyre Age (0 at race start)
                0                                  # Pit Stop History (0 = no stop yet)
            ]

        return self.state

    def step(self, action):
        """
        Step the environment forward by one lap.
        """
        # Decode the action
        pace_strategy = action // 6
        pit_decision = (action % 6) // 3
        tyre_choice = action % 3

        # Example of how action affects the race:
        # - Higher pace = faster lap time but higher degradation
        # - Pit decision = lose time but reset tyre age
        # - Tyre choice = affects future lap times

        for i in range(self.num_drivers):
            if pit_decision == 1:
                # If the driver pits → Reset tyre age and change tyre type
                self.state[i][5] = 0  # Reset tyre age
                self.state[i][4] = tyre_choice  # Change tyre type
                self.state[i][6] += 1  # Increment pit stop count
            else:
                # Increase tyre age
                self.state[i][5] += 1

            # Adjust pace based on tyre type and age
            if pace_strategy == 0:  # Push
                lap_penalty = 0.1 * self.state[i][5]
            elif pace_strategy == 1:  # Defend
                lap_penalty = -0.05 * self.state[i][5]
            else:  # Manage
                lap_penalty = 0

            # Simulate lap time increase based on degradation
            self.state[i][2] += lap_penalty

        # Increment lap count
        self.current_lap += 1

        # Check if race is over
        done = self.current_lap > len(self.race_data['lap_times'])

        # Reward function:
        # - Higher position = higher reward
        # - Successful undercut = bonus
        # - Tyre degradation penalty
        reward = 0
        for i in range(self.num_drivers):
            position = self.state[i][1]
            reward += (self.num_drivers - position) * 0.1

            if pit_decision == 1:
                if i > 0 and self.state[i][2] < self.state[i - 1][2]:
                    reward += 0.5  # Successful undercut
                else:
                    reward -= 0.3  # Pit failure

        return self.state, reward, done, {}

    def render(self, mode='human'):
        """
        Render the current race state.
        """
        print(f"\nLap: {self.current_lap}")
        print("Pos | Gap to Leader | Gap to Car Ahead | Tyre Type | Tyre Age | Pit Stops")
        for i in range(self.num_drivers):
            print(f"{int(self.state[i][1]):3} | {self.state[i][2]:12.3f} | {self.state[i][3]:14.3f} |"
                  f" {int(self.state[i][4]):9} | {int(self.state[i][5]):8} | {int(self.state[i][6]):9}")

    def close(self):
        """
        Close the environment.
        """
        pass

# Example setup
example_race = races_cleaned[list(races_cleaned.keys())[0]]
env = F1RaceEnv(example_race)
state = env.reset()
env.render()

# Take a sample action
sample_action = env.action_space.sample()
new_state, reward, done, _ = env.step(sample_action)
env.render()

print(f"\nAction Taken: {sample_action}, Reward: {reward}, Done: {done}")

