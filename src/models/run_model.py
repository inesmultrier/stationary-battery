import gym
from pathlib import Path
from battery_model import HouseSystem
import pandas as pd
from ray import tune
import ray
from ray.tune import grid_search
from gym.spaces import Box, Discrete, MultiDiscrete
import numpy as np
import time
import inspect


class BatteryEnv(gym.Env):
    def __init__(self, env_config):
        self.battery_size = env_config["battery_size"]
        self.max_charge_rate = env_config["max_charge_rate"]
        self.time_scale = env_config["time_scale"]
        self.consumption_data = "/data/processed/conso_train_604.csv"  # env_config["consumption_data"]
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        print("calframe: {}".format(calframe))
        self.setup_environment(self.battery_size, self.consumption_data, self.max_charge_rate, self.time_scale)
        self.rewards = []

    def reset(self):
        results = pd.DataFrame.from_dict(self.house_system.run_data, "index")
        project_dir = Path(__file__).resolve().parents[2]
        timestr = time.strftime("%Y-%m-%d-%H-%M-%S")
        results_path = (
            "{}/data/results/run_data_battery_{}_time_{}.csv".format(
                project_dir, self.battery_size, timestr
            )
        )
        results["reward"] = self.rewards
        results.to_csv(results_path)

        self.setup_environment(self.battery_size, self.consumption_data, self.max_charge_rate, self.time_scale)
        self.rewards.clear()
        return self.start_obs

    def step(self, action):
        observations, reward, done, info = self.house_system.step(
            action[0]
        )
        print("reward during step", reward)
        self.rewards.append(reward)

        return observations, reward, done, info

    def render(self):
        pass

    def setup_environment(self, battery_size, consumption_data, max_charge_rate, time_scale):
        action_space = Box(low=-max_charge_rate, high=max_charge_rate, shape=(1,), dtype=np.float32)
        observation_space = Box(low=-300000, high=300000, shape=(5,), dtype=np.float32)

        self.observation_space = observation_space
        self.action_space = action_space

        project_dir = Path(__file__).resolve().parents[2]

        consumption_data_path = "{}{}".format(project_dir, consumption_data)

        consumption_data = pd.read_csv(
            consumption_data_path,
        )

        self.house_system = HouseSystem(battery_size=battery_size, input_data=consumption_data,
                                        max_charge_rate=max_charge_rate, time_scale=time_scale)

        self.start_obs = [
            self.house_system.battery.battery_size,
            self.house_system.battery.current_charge,
            0,
            0,
            0,
        ]


if __name__ == "__main__":
    ray.init()

    config = {
        "env": BatteryEnv,
        "lr": 0.0297,  # tune.uniform(1e-7, 1e-1),  # try different lrs
        "actor_hiddens": [200, 200],  # tune.grid_search([[200, 200], [300, 300], [400, 400]]),
        "critic_hiddens": [300, 300],  # tune.grid_search(
        # [[200, 200], [300, 300], [400, 400], [500, 500]]
        # ),
        "num_workers": 1,  # parallelism,
        "timesteps_per_iteration": 2500,
        "env_config": {
            # "battery_size": grid_search(
            #     [0.2, 0.4, 0.6, 0.8, 1, 1.2, 1.4, 1.6, 1.8, 2.0]
            # ),
            "consumption_data": "/data/processed/conso_train_604.csv",
            "battery_size": 15400,
            "max_charge_rate": 13500,
            "time_scale": 0.25,
        },
    }

    stop = {
        "training_iteration": 30,
    }

    # results = tune.run("DDPG", config=config, stop=stop, checkpoint_freq=1)
    # results = tune.run(["PPO"], config=config, stop=stop, checkpoint_freq=1)
    results = tune.run(
        "DDPG", config=config, stop=stop, checkpoint_freq=1, num_samples=1
    )
