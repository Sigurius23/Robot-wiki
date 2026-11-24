# Simulation setup: NavDP benchmark and Geoff-Sim

We test navigation stacks in simulation before anything runs on the G1. Two prebuilt
setups cover the first stages; this guide installs both on the RTX 5090 lab laptop.

| Setup | Stage | What it gives us | Robot body |
|---|---|---|---|
| **NavDP benchmark** ([repo](https://github.com/InternRobotics/NavDP)) | Model comparison, closed loop | GNM, ViNT, NoMaD, NavDP and X-NavDP already wired in as policy servers; cluttered and home scenes in Isaac Sim; image-goal, point-goal and no-goal tasks | Wheeled |
| **Geoff-Sim** ([repo](https://github.com/DavidBatty95/Geoff-Sim)) | Full stack on a G1 | Walking G1 (official Unitree policy, velocity commands) in MuJoCo with ROS 2 Humble, LiDAR, RGB-D, IMU, real-robot DDS topics, Nav2, SLAM and walking pedestrians | Unitree G1 |

Why these two (checked November 2026): no public benchmark yet combines a walking G1,
navigation models and pedestrians in one photoreal simulator. HumanoidVLN would, but its
code is "coming soon". Isaac Lab 3.0 has no G1 navigation task. Arena 5.0 (October 2026)
is the best social-navigation benchmark but only has wheeled and quadruped robots; it is
listed under "Later" below.

## Ground rules on the laptop

- **Keep environments separate.** Do not install anything into `~/venvs/vnm` (the route
  test). The NavDP benchmark gets its own conda environment with Python 3.10; Geoff-Sim
  runs in Docker.
- **The laptop runs Ubuntu 26.04 and Python 3.14,** newer than either project expects.
  Conda provides Python 3.10 for NavDP, and Docker provides ROS 2 Humble for Geoff-Sim, so
  neither touches the system Python.
- **Licenses:** NavDP code and the InternUtopia scenes are CC BY-NC-SA 4.0 (non-commercial).
  Geoff-Sim has mixed per-package licenses (Apache-2.0 and BSD-3-Clause), pedestrian assets
  with unclear redistribution rights, and a downloaded Unitree policy under its own terms.
  Fine for internal testing; do not commit their assets, scenes or checkpoints to
  Robot-wiki (it is public).
- **Stop and report** if a step fails in a way this guide does not cover, rather than
  working around it by changing system packages or drivers.

---

## Part A: NavDP benchmark (Isaac Sim 4.2)

### A0. The main risk: Isaac Sim 4.2 on an RTX 5090

NavDP pins Isaac Sim 4.2.0 and Isaac Lab 1.2.0. NVIDIA's current requirements page lists
RTX 50-series GPUs for Isaac Sim 6.x, but we found no statement that 4.2 runs on Blackwell
GPUs. Step A2 checks this first. If Isaac Sim 4.2 does not start, stop Part A and report
the error; Part B does not depend on Isaac Sim.

### A1. Conda

Install Miniforge (or Miniconda) if `conda` is not present.

### A2. Isaac Sim 4.2 and Isaac Lab 1.2 (commands from the NavDP README)

```bash
conda create -n isaaclab python=3.10
conda activate isaaclab
pip install --upgrade pip
pip install isaacsim==4.2.0.2 isaacsim-extscache-physics==4.2.0.2 isaacsim-extscache-kit==4.2.0.2 isaacsim-extscache-kit-sdk==4.2.0.2 --extra-index-url https://pypi.nvidia.com
isaacsim omni.isaac.sim.python.kit        # must open without GPU errors
```
```bash
git clone https://github.com/isaac-sim/IsaacLab.git ~/IsaacLab_1.2
cd ~/IsaacLab_1.2 && git checkout tags/v1.2.0
./isaaclab.sh -i                          # NavDP says to ignore an "rsl-rl unavailable" error
./isaaclab.sh -p source/standalone/tutorials/00_sim/create_empty.py
```

**Checkpoint:** both test commands must run. Record the PyTorch and CUDA versions inside
this environment (`python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`).
If PyTorch cannot see the RTX 5090 (an older CUDA build), report it before continuing.

### A3. NavDP and the baseline dependencies

```bash
git clone https://github.com/InternRobotics/NavDP.git ~/NavDP
cd ~/NavDP && pip install -r requirements.txt
pip install efficientnet_pytorch==0.7.1 diffusers==0.33.1
pip install git+https://github.com/real-stanford/diffusion_policy.git
```

GNM, ViNT and NoMaD may also need the extras found during the route test
(`einops`, `warmup_scheduler`, `wandb prettytable tqdm lmdb`); install them into this
environment only if a server fails to start because one is missing.

### A4. Scenes

Download the evaluation scenes from
[InternScene-N1 on Hugging Face](https://huggingface.co/datasets/InternRobotics/Scene-N1/tree/main/n1_eval_scenes):
`SkyTexture.tar.gz`, `Materials.tar.gz`, `cluttered_easy.tar.gz`, `cluttered_hard.tar.gz`,
`internscenes_commercial.tar.gz` and the `internscenes_home` folder. Unpack under
`~/NavDP/assets/scenes/` as `SkyTexture/`, `Materials/`, `cluttered_easy/`,
`cluttered_hard/`, `internscenes_commercial/` and `internscene_home/` (folder names as in
the NavDP README). Start with `cluttered_easy` alone if disk or time is short.

### A5. Checkpoints

- **GNM, ViNT, NoMaD:** the same Google Drive folder as the route test. Copy the three
  files already in `~/visualnav-transformer/deployment/model_weights/` instead of
  downloading again. Check each `baselines/<name>/` folder for where its server expects
  the file.
- **X-NavDP:** `x-navdp_posttrain.ckpt` from
  [huggingface.co/InternRobotics/X-NavDP](https://huggingface.co/InternRobotics/X-NavDP).
- **NavDP:** needs a request form (linked in the NavDP README). That is for a person to
  fill in; skip NavDP until the checkpoint arrives.

### A6. Run

Each baseline has a server in `baselines/<name>/`. The README only shows NavDP's command:
```bash
cd ~/NavDP/baselines/navdp/
python navdp_server.py --port 8888 --checkpoint ./checkpoints/navdp_checkpoint.ckpt
```
For GNM, ViNT, NoMaD and X-NavDP, read the server file's arguments (`python <server>.py --help`)
and start it the same way on its own port. Then, in a second terminal in the same
environment, run the evaluation against that port:
```bash
python eval_imagegoal_wheeled.py --port {PORT} --scene_dir {ABSOLUTE_SCENE_DIR} --scene_index {INDEX} --scene_scale {SCALE}
python eval_nogoal_wheeled.py    --port {PORT} --scene_dir {ABSOLUTE_SCENE_DIR} --scene_index {INDEX} --scene_scale {SCALE}
python eval_pointgoal_wheeled.py --port {PORT} --scene_dir {ABSOLUTE_SCENE_DIR} --scene_index {INDEX} --scene_scale {SCALE}
```
- `--scene_dir` must be an **absolute** path.
- `--scene_scale`: `1.0` for the cluttered scenes, `0.01` for InternScenes.
- GNM, ViNT and NoMaD support image-goal and no-goal only. NavDP and X-NavDP also do
  point-goal.

**First milestone:** GNM on `cluttered_easy`, image-goal, one scene index, end to end.
Then all three models on the same scenes and indices, then X-NavDP.

**Report back:** success rate and SPL (or whatever the eval scripts print) per model,
task and scene, plus any crashes.

---

## Part B: Geoff-Sim (G1 in MuJoCo, ROS 2 Humble in Docker)

### B1. Host requirements (from the Geoff-Sim README)

x86-64 Ubuntu/Debian, Docker with Compose v2, `/dev/dri`, and an X11 or XWayland display.
The README says simulation does not need an NVIDIA GPU (GPU support is for training).
After installing Docker, log out and back in if you get "permission denied".

### B2. Install and first demo (verbatim from the README)

```bash
git clone --recurse-submodules https://github.com/DavidBatty95/Geoff-Sim.git ~/Geoff-Sim
cd ~/Geoff-Sim
./install.sh
./scripts/run_onboard_navigation_demo.sh
```

`install.sh` downloads the official Unitree locomotion policy and checks its checksum;
it must pass.

### B3. Pedestrian scenes and a scored run

From the Geoff-Sim demo guide:
```bash
./geoff worlds                                         # list worlds
./geoff demo cafe --people 4 --duration 300 --fast-start
./scripts/run_demo_suite.sh --case onboard-waypoints --goals 8 --headless --seed 42
```

**First milestone:** the G1 walks through the cafe with pedestrians, then the headless
8-goal suite finishes and writes its scores.

### B4. Map the interfaces we will plug into

Inside the running container:
```bash
ros2 topic list
ros2 topic info -v /odom
```
Record the exact topics for: velocity commands to the walking policy, RGB and depth
images, LiDAR (`/onboard/lidar` is documented), odometry (`/odom`), the Nav2 goal, and the
map (`/map`). The README states ROS 2 middleware `rmw_cyclonedds_cpp` and
`ROS_DOMAIN_ID=42`. These topics are where our MPPI planner, safety cage and the
GNM/ViNT bridge will connect later.

**Report back:** whether install and both milestones worked, the headless suite scores,
and the topic list.

Known limitation from the README: onboard navigation is experimental, and live trials
include collisions and timeouts. That is the baseline our stack has to beat.

---

## Later (not part of this setup)

| Tool | Use | Why later |
|---|---|---|
| [Arena 5.0](https://github.com/Arena-Rosnav) (MIT, ROS 2 Humble, Isaac Sim) | Social-navigation benchmark: HuNavSim pedestrians, Nav2 MPPI/DWB baselines, social metrics, scenario generation | Wheeled and quadruped robots only; strong for testing our planner and safety cage in crowds with a stand-in body |
| [mjlab](https://github.com/mujocolab/mjlab) / [unitree_rl_mjlab](https://github.com/unitreerobotics/unitree_rl_mjlab) (Apache-2.0) | Train our own G1 velocity policy, export ONNX, test in `unitree_mujoco` | No pretrained G1 checkpoint; only if the official policy limits us |
| [unitree_sim_isaaclab](https://github.com/unitreerobotics/unitree_sim_isaaclab) (Isaac Sim 6.2, Isaac Lab 3.0) | Photoreal G1 head-camera images with the real robot's DDS interface | Built for manipulation; no navigation or pedestrians |
| [HumanoidVLN](https://humanoid-vln.github.io/) | G1 language-navigation benchmark in Isaac Sim | Code not released yet |
