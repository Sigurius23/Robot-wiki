# Offline route test: GNM vs ViNT vs NoMaD

Compares the three pretrained visual navigation models from
[robodhruv/visualnav-transformer](https://github.com/robodhruv/visualnav-transformer)
on walks recorded in our own building, before any of them is allowed near the G1.
It is step 4 of the build order in
[MODEL_INVENTORY_AND_BEST_STACK.md](../../wiki/methods/architecture%20brainstorming/MODEL_INVENTORY_AND_BEST_STACK.md)
(Combination D) and follows the protocol of the 2026 real-world evaluation
[arXiv 2603.25937](https://arxiv.org/abs/2603.25937).

You record one walk along a route (this becomes the topological map), then
several test walks along the same route with obstacles, people and lighting
changes. Each test walk is replayed through every model exactly as upstream
`navigate.py` would run on a robot, and the outputs are compared.

## What this test can and cannot tell you

| It measures | It cannot measure |
|---|---|
| Whether the model knows where it is on the route (node tracking) | Collisions: the robot never acts on the outputs (open loop) |
| Whether it calls "goal reached" too early | How the model reacts to its own mistakes, since the camera follows your walk, not its commands |
| Whether predicted waypoints bend away from an obstacle while it is in view | Social behavior around people beyond "did it bend away" |
| Latency and peak VRAM on the RTX 5090 | Performance on the Orin NX |

A model that passes here goes to **shadow mode on the robot** (it runs live but
Nav2 drives), not straight to control. None of these models is ever the collision
safety layer.

## Files

| File | What it does |
|---|---|
| `make_synthetic.py` | Makes a fake corridor walk to check the pipeline (no real data) |
| `extract_frames.py` | Video or image folder → evenly timed frames + `meta.json` |
| `build_topomap.py` | Route frames → topomap nodes `0.png, 1.png, …` (one per `--dt` seconds, like upstream) |
| `run_replay.py` | Replays a test walk through the models; writes `<model>.jsonl` and `<model>.meta.json` |
| `report.py` | Comparison table (`report.md`) and plot (`report.png`) |
| `annotations.example.yaml` | Template for marking goal frame, position checkpoints and obstacles |
| `common.py` | Model loading and inference (mirrors upstream `utils.py` / `navigate.py`) and the dry-run stand-in |

`data/` and `results/` are git-ignored.

## 1. Check the pipeline (any machine, no GPU)

Needs Python 3.10+, `numpy pillow opencv-python pyyaml matplotlib`.

```bash
python make_synthetic.py --out data/synth --fps 4
python extract_frames.py --src data/synth/route.mp4 --out data/synth/route --fps 4
python extract_frames.py --src data/synth/test.mp4 --out data/synth/test --fps 4
python build_topomap.py --frames data/synth/route --out data/synth/topomap --dt 1.0
python run_replay.py --topomap data/synth/topomap --test data/synth/test --dry-run --out results/dry
python report.py --results results/dry --annotations data/synth/annotations.yaml
```

The dry-run "model" is a numpy image comparison, not a navigation model; its
numbers only show that every step works.

## 2. Set up the RTX 5090 laptop (Ubuntu)

1. **Clone upstream** (anywhere, e.g. `~/visualnav-transformer`):
   ```bash
   git clone https://github.com/robodhruv/visualnav-transformer.git ~/visualnav-transformer
   ```
2. **Python environment.** The RTX 5090 (Blackwell) needs a PyTorch build for CUDA 12.8 or newer.
   Upstream's conda files may pin an older PyTorch, so use your own environment and install
   PyTorch first, choosing the CUDA 12.8+ build on the selector at pytorch.org, for example:
   ```bash
   python3 -m venv ~/venvs/vnm && source ~/venvs/vnm/bin/activate
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
   python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```
   Then the upstream packages:
   ```bash
   cd ~/visualnav-transformer && pip install -e train/
   git clone https://github.com/real-stanford/diffusion_policy.git ~/diffusion_policy
   pip install -e ~/diffusion_policy --config-settings editable_mode=compat
   pip install diffusers efficientnet_pytorch einops opencv-python pyyaml matplotlib
   ```
   - `diffusion_policy/` has no `__init__.py`, so a normal editable install registers nothing.
     `editable_mode=compat` adds the repo to the import path instead.
   - `einops` is needed by the model code but not pulled in by the installs above.
   - If `pip install -e train/` tries to replace your PyTorch, rerun it with `--no-deps` and
     install whatever it then reports missing. ROS is **not** needed.

   Check that all three model classes import before going further:
   ```bash
   python -c "from vint_train.models.gnm.gnm import GNM; from vint_train.models.vint.vint import ViNT; from vint_train.models.nomad.nomad import NoMaD; from diffusion_policy.model.diffusion.conditional_unet1d import ConditionalUnet1D; print('imports ok')"
   ```

   Tested on the lab laptop (November 2026): Ubuntu 26.04, Python 3.14, NVIDIA driver 595.99,
   PyTorch 2.11 built for CUDA 12.8. Newer versions than these instructions assume worked.
3. **Weights.** Download from the "Pre-Trained Models" Google Drive link in the upstream
   README and save them with these names (from upstream `deployment/config/models.yaml`):
   ```
   ~/visualnav-transformer/deployment/model_weights/gnm_large.pth
   ~/visualnav-transformer/deployment/model_weights/vint.pth
   ~/visualnav-transformer/deployment/model_weights/nomad.pth
   ```
   Only use files from that official link: the GNM and ViNT checkpoints are full pickled
   models, and loading a pickle runs code.

4. **Smoke test with the real models.** Run the step 1 dry run on the laptop first, then the
   same synthetic walk through the real weights:
   ```bash
   python run_replay.py --topomap data/synth/topomap --test data/synth/test \
       --vnm-repo ~/visualnav-transformer --models gnm vint nomad --out results/smoke
   ```
   Pass if no "checkpoint mismatch" warning appears and each model prints a peak VRAM and a
   median latency. Tracking numbers on synthetic data mean nothing.

## 3. Record the walks

- **Camera:** ideally the G1's own RealSense D435i colour stream; otherwise a phone. Hold it at
  the G1's camera height (measure it on the robot) and pointing forward, as steady as you can.
- **Speed:** walk at a steady pace close to the G1's (about 0.5 m/s).
- **Route:** 20–60 m through the space the robot will use, with at least one turn.

| Walk | What to do | What it tests |
|---|---|---|
| `route` | Clean walk, start to goal | Becomes the topomap |
| `repeat` | Same walk again, nothing changed | Baseline tracking and goal detection |
| `obstacle_left`, `obstacle_right` | Chair or box placed beside the path; walk past it | Do waypoints bend away? |
| `person` | Someone walks across or toward you | Dynamic obstacle response |
| `lighting` | Different lights or time of day | Robustness to appearance change |
| `repetitive` | A section with similar-looking doors or panels | Known weakness: early goal calls and lost tracking |
| `turn_check` | Short walk with one clear left turn | Confirms the sign of the lateral waypoint axis (below) |

With a RealSense `.bag` recording, export the colour frames to PNGs first (for example with
the RealSense SDK's `rs-convert`) and pass the folder with `--src-fps 30`.

## 4. Run it

```bash
python extract_frames.py --src recordings/route.mp4 --out data/route --fps 4
python build_topomap.py --frames data/route --out data/topomap --dt 1.0
python extract_frames.py --src recordings/obstacle_left.mp4 --out data/obstacle_left --fps 4
cp annotations.example.yaml data/obstacle_left/annotations.yaml   # then edit the frame numbers
python run_replay.py --topomap data/topomap --test data/obstacle_left \
    --vnm-repo ~/visualnav-transformer --models gnm vint nomad --out results/obstacle_left
python report.py --results results/obstacle_left --annotations data/obstacle_left/annotations.yaml
```

Repeat the last four lines for each test walk. Defaults follow upstream `navigate.py`:
`--radius 4 --close-threshold 3 --waypoint 2 --num-samples 8`. `--fps` sets the control rate
the models see (4 Hz by default); `--max-v` only scales the metric waypoint column.

**Annotating:** open the frames in `data/<walk>/` next to the topomap images in
`data/topomap/` and fill in `goal_frame`, a few `checkpoints` (frame → node) and the
`obstacles` segments. Without checkpoints, node error assumes you walked at constant speed.

**Lateral sign check:** the report assumes waypoint `y > 0` means left. In the
`turn_check` walk the waypoints during the left turn should be positive. If they are
negative, add `--lateral-sign -1` to every `report.py` call.

## 5. Read the results

| Column | Good result |
|---|---|
| Final node / Reached goal | Reaches the last node |
| Early goal call | `False`. Calling the goal early was the main failure in the 2026 evaluation |
| Node error (MAE) | Within about 1–2 nodes of the checkpoints |
| Backward jumps | Few; many jumps mean it keeps losing its place |
| Steered away | Most obstacle segments, with a clear lateral shift |
| Latency p95 / Max rate | Comfortably above the control rate (4 Hz → p95 well under 250 ms) |
| Peak VRAM | Small enough to sit beside Nav2 and a swapped-in VLM in 24 GB |
| Checkpoint key mismatches | `0`. Anything else means the weights did not load properly |

These thresholds are our suggestion, not from a paper. **Promote to shadow mode** the model
that reaches the goal without early calls on `repeat`, `lighting` and `repetitive`, and bends
away in most obstacle walks. Record the decision and the `report.md` tables in the wiki.

## Notes

- The model code in `common.py` mirrors upstream (MIT license, Copyright (c) 2023 Dhruv Shah
  et al.). It is copied rather than imported because upstream `utils.py` imports ROS 1.
- NoMaD samples are random; `--seed` fixes them so runs are repeatable.
- The models were trained mostly on wheeled-robot camera views. The G1's higher camera and
  narrower D435i field of view may hurt them; that is exactly what this test should reveal.
