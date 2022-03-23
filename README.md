
stationary-battery
==============================

This project optimizes domestic batteries with domestic solar photovoltaics attached.

Installation
============

Installation of packages
------------------------


```bash
> pip install -r requirements.txt
```

Usage
-----

To run the reinforcement learning algorithm:

```bash
> python src/models/run_model.py   
```

Training
--------

To visualise the training in real-time, it is possible to use tensorboard. To start tensorboard, you must find your `ray_results/` folder. This is usually in `~/ray_results/`. The following code should work to get tensorboard started:

```bash
> tensorboard --logdir=~/ray_results/
```

You can then view the training by navigating to `http://localhost:6006/` in a browser.

Evaluate the model
-------------------
```rllib evaluate /Users/InesMultrier/ray_results/DDPG/DDPG_BatteryEnv_1c8e4_00000_0_2022-02-28_18-34-34/checkpoint_000030/checkpoint-30 --run DDPG --env BatteryEnv --steps 10079  --local-mode --save-info --out rollouts.pkl```
