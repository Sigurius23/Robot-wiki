---
title: Model Inventory and Recommended Stack
tags: [architecture, models, navigation, hardware, vram]
date_updated: 2026-11-24
---

# Model Inventory and Recommended Stack

This note lists every model and major component the G1 project has considered, with a verdict for each, and ends with the stack we recommend building first.

It covers the brainstorming docs in this folder, the launchpad pages in `g1-jepa-tethered/docs`, and Jan's proposal slides. VRAM and rate figures are copied from those sources. None of them have been measured on our hardware yet.

**Verdicts used below**

- **Use now:** part of the recommended first build.
- **Shadow test:** run beside the real stack and compare, without control of the robot.
- **Later:** worth adding once a specific mode or scenario needs it.
- **Alternative:** a reasonable substitute if the chosen option fails.
- **Dropped:** rejected, with the reason given.
- **Reference:** cited as background only, never planned for deployment.

---

## 1. Route planning and navigation

| Model / component | Where it came from | Verdict | Why |
|---|---|---|---|
| **Nav2** (global route planning) | Jan's proposal; curriculum doc | **Use now** | Metric goals, works with FAST-LIO2 maps, ROS 2 native. Used for routing only, not as the whole classical stack the curriculum doc rejected. |
| **ViNT** (Visual Navigation Transformer) | Jan's proposal | **Shadow test** | Small and pretrained, but it needs a pre-recorded image route and gives no metric safety. Compare against Nav2 before trusting it. |
| **Geometric MPPI** (trajectory + tracked obstacles) | Jan's proposal; block diagram; crowd stack | **Use now, onboard** | Fast local planning around people. Does not depend on V-JEPA rollouts, so the feasibility objection does not apply. Orin NX load still needs profiling. |
| **Latent MPPI** (1024 samples × 15 steps on V-JEPA 2) | Original V1 design | **Dropped** | About 100–1000× beyond the RTX 5090's budget (feasibility review). |
| **A\* / RRT\*** through the voxel grid (Active Neural SLAM decomposition) | Literature improvements; revised architecture | **Alternative** | Sub-millisecond and proven. Nav2's global planner covers this role in the recommended stack. |
| **DWA / TEB** (Nav2 local planners) | Curriculum doc | **Dropped** | About 100 ms reaction and freezing in dense crowds. |
| **π0.5 flow-matching routing** | Curriculum level 7; crowd stack | **Later** | Only if MPPI freezes or fails in dense crowds. |
| **AG-SLAM information-gain planner** | Frontiers deep dive; swap page (V3) | **Later** | Useful for active exploration, not needed for point-to-point routes. |
| **Uni-LaViRA** (zero-shot language navigation) + **NavDP** local planner | Uni-LaViRA analysis | **Later** | No training and shown on a G1, but about 1 Hz and about 22,000 tokens per step. A candidate for the Search mode. |

## 2. Perception and people tracking

| Model / component | Where it came from | Verdict | Why |
|---|---|---|---|
| **LV-DOT** (LiDAR-visual dynamic obstacle tracker, with AEKF) | Jan's proposal; crowd stack; mapping doc | **Use now, onboard** | Tracks people with position and velocity. About 200 MB, 30 Hz on the Orin NX per the mapping doc. |
| **YOLOv11-pose** | Crowd stack; mapping doc | **Use now if the Orin NX has room** | Adds body keypoints and heading for social cues. About 1.8 GB, 30 Hz on the Orin NX per the mapping doc. |
| **DINOv3** (ViT-L distilled) | Revised architecture; V2 orchestrator | **Later** | Dense semantic features for the voxel map and grounding. Not needed for the first navigation build. |
| **DINO / DINOv2** | Literature improvements; roadmap | **Reference** | Background for DINOv3; DINOv2 was an early encoder option in the roadmap. |
| **SigLIP** | Roadmap Phase 2; PaliGemma's vision tower | **Reference** | Mentioned as a lightweight encoder option. |
| **Slot Attention** | Original V1 design | **Dropped** | Only validated on synthetic data; DINO already segments objects without it. |
| **SAM 2 / DEVA** | Feasibility review | **Alternative** | Suggested as faster substitutes for Slot Attention; never adopted. |
| **SAM / Grounding DINO** | Uni-LaViRA analysis | **Later** | Helpers for grounding vague areas such as "the kitchen", if Uni-LaViRA is used. |

## 3. Localization, mapping and safety geometry

| Model / component | Where it came from | Verdict | Why |
|---|---|---|---|
| **FAST-LIO2** (LiDAR-inertial odometry) | Every architecture version | **Use now, onboard** | Metric pose that MPPI and Nav2 both need. Missing from Jan's proposal. |
| **Local occupancy + ESDF** (Voxblox) | 3D scene review; architecture page; swap page | **Use now, onboard** | The authority for collision clearance. |
| **OctoMap** | 3D scene review | **Alternative** | Probabilistic 3D occupancy with explicit unknown space. |
| **Sparse voxel memory** (MinkowskiNet, VoxFormer) | Revised architecture; V2 orchestrator | **Later** | Prediction memory and the rear blind spot. About 2 GB at 10 cm voxels. |
| **4D-NVS / HexPlane** | Original V1 design | **Dropped** | Built for rendering new views, not for real-time robotics; cost 4 GB. |
| **Semantic 3D Gaussian Splatting map** (GPS-SLAM, LCD-Splat, WildGS-SLAM, GARAD-SLAM, Splat-Nav) | Frontiers deep dive; mapping doc; 3D scene review | **Later** | Visual and semantic context for social mode. LCD-Splat/AG-SLAM costs about 6.5 GB per the mapping doc. It must never certify a path on its own. |
| **GPU 2.5D elevation map** | Mapping doc | **Later** | Footstep terrain checks on stairs and rough ground. About 0.8 GB. |

## 4. World models and predictive models

| Model / component | Where it came from | Verdict | Why |
|---|---|---|---|
| **V-JEPA 2 / V-JEPA 2.1** | Original V1 design; VRAM measurements | **Dropped from the control loop** | Only worth it inside latent MPPI, which was dropped. About 7.3 GB (1B) or 10–12 GB (2B) at BF16. |
| **LeJEPA** (ViT-L, 304M) | Literature improvements; revised architecture | **Later (research)** | A smaller encoder for G1-specific pretraining if a learned world model comes back. |
| **VL-JEPA** | Original V1 design | **Dropped** | Replaced by off-the-shelf VLMs and VLAs. |
| **Acoustic-JEPA** | Original V1 design | **Dropped** | Out of scope in the compute budget review. |
| **VICReg, WorldRFT** | Original V1 design | **Dropped** | Parts of the V1 "kitchen sink" removed in the revision. |
| **I-JEPA, EchoJEPA** | Literature improvements | **Reference** | Evidence for predicting in representation space and noise robustness. |
| **Genie / Genie 2** | Literature improvements; state of the art doc | **Reference** | Latent-action idea only; far too large to run. |
| **Cosmos 3** (Nano, Super, Edge) | Variations 2, 4, 5, 8, 10; Cosmos VLM page; block diagram | **Later (future hardware)** | Cosmos 3 Nano needs 48 GB+ at FP8 per the V2 orchestrator. Policy mode needs about 17 GB even at NVFP4. Revisit with Jetson Thor or a bigger GPU. |

## 5. Language and vision-language models

| Model | Where it came from | Verdict | Why |
|---|---|---|---|
| **Cosmos-Reason2-2B** (W4A16) | V2 orchestrator; state of the art doc | **Use in the swap slot (Search mode)** | Finds people and answers scene questions. Shares a backbone with GR00T N1.7. |
| **Gemma 4 12B** | LLM and VLM roles doc | **Alternative** | Local, open, multimodal, about 12 GB at INT8. The roles doc rated it the most practical general VLM. |
| **PaliGemma 3B** | Revised architecture; crowd stack | **Alternative** | Light goal selector or social-intent classifier, about 6 GB at INT8. |
| **Qwen3.5-9B / Gemini 3.1 Pro** | Uni-LaViRA analysis | **Later** | Only as part of a Uni-LaViRA Search mode. |
| **GLM-5.1** | LLM and VLM roles doc | **Dropped for runtime** | Cloud only, no vision, needs internet. Could still help offline with planning or code. |
| **Omni-LLM / Llama-3-Omni** | Curriculum level 8; crowd stack | **Later** | Spoken dialogue for the social interaction scenario. |

## 6. Vision-language-action models

| Model | Where it came from | Verdict | Why |
|---|---|---|---|
| **GR00T N1.7** | V2 orchestrator; Uni-LaViRA comparison | **Use in the swap slot (Manipulation mode)** | Contact-rich arm and hand control, about 10–12 GB at FP16. Needs our own demonstrations and fine-tuning first. |
| **GR00T N1.5 / N1** | Revised architecture; variations 3, 4, 10 | **Superseded** | Earlier versions of GR00T N1.7. |
| **SONIC** (GR00T's onboard motion decoder) | V2 orchestrator | **Later** | Decodes GR00T motion tokens at 50 Hz on the robot, needed with GR00T. |
| **π0 / π0.5** | Variation 6; frontiers deep dive; swap page | **Alternative** | Flow-matching manipulation policy, about 6–8 GB. |
| **SmolVLA** | Compute budget | **Alternative** | Lighter, faster VLA. |
| **OpenVLA** | Compute budget | **Dropped** | About 6 Hz, too slow. |
| **UnifoLM-VLA-0** | State of the art doc | **Later (Thor path)** | End-to-end option once compute moves onboard. |
| **Figure Helix, RT-1, RT-2, Mobile ALOHA** | State of the art doc; camera evaluation | **Reference** | Proprietary or background examples. |

## 7. Walking, whole-body control and safety (onboard)

| Model / component | Where it came from | Verdict | Why |
|---|---|---|---|
| **Unitree native locomotion controller** (velocity commands) | Uni-LaViRA G1 deployment | **Use now** | Walking works on day one with no gait training. |
| **ULTRA** whole-body control | Literature improvements; revised architecture | **Next** | G1-validated training pipeline when native walking is not enough. |
| **HUGWBC, ASAP, FPO++** | Literature improvements; swap page | **Alternative** | Other G1-validated whole-body control approaches. |
| **Jan's mixture-of-experts motion policy** (depth CNN + state + path, 4 or 13 experts, outputs 29 joint targets plus gains, 50 Hz) | Jan's proposal | **Later** | Perceptive walking for rough terrain or parkour. The most expensive part to train, and it leaves out the 14 hand joints. |
| **Humanoid Parkour training recipe** (fractal terrain, D435i noise model) | Roadmap; parkour paper note | **Later** | Training reference for any learned walking policy. |
| **CBF** (proprioceptive and ESDF-based safety filter) | Every architecture version | **Use now, onboard** | Hard safety layer under every planner. |
| **Watchdog + 500 ms trajectory buffer** | Original design onward | **Use now, onboard** | Safe stop on link loss. Jan's proposal does not cover this. |
| **FIRM** fall prevention and recovery | Literature improvements; revised architecture | **Later** | Validated on the G1; add once walking is stable. |
| **HJI reachability** | Original V1 design | **Dropped** | Open research problem in latent space. |

## 8. New models found (web check, 2026-11-24)

These were found in a web search and checked on their arXiv, GitHub, Hugging Face or NVIDIA pages. They are additions; the verdicts in sections 1–7 are unchanged.

| Model / component | Date | What it is | Relevance to us | Available now? | Verdict |
|---|---|---|---|---|---|
| **OpenBelief-Nav** ([arXiv 2608.13923](https://arxiv.org/abs/2608.13923)) | Aug 2026 | Open-vocabulary object memory for language-guided search, with re-grounding when arrival RGB-D verification fails | Run on a Unitree G1 with Livox MID-360 and RealSense D435i, RTX 5090 workstation offboard, Nav2 on an onboard Jetson AGX Orin. Almost exactly our split. | Code promised on acceptance ([project page](https://openbelief-nav.github.io/)) | **Watch; template for Search mode** |
| **SONIC** in GR00T Whole-Body Control ([GitHub](https://github.com/NVlabs/GR00T-WholeBodyControl)) | Feb 2026, v1.1 checkpoint Jul 2026 | Pretrained humanoid whole-body controller, 50 Hz, C++/TensorRT | Three G1 checkpoints downloadable. An end-to-end GR00T N1.7 + SONIC VLA workflow on G1 was added May 2026. Orin support added. | Yes. Code Apache-2.0, weights NVIDIA Open Model License | **Next (walking and Mode 3)** |
| **TANGO** ([arXiv 2609.09158](https://arxiv.org/abs/2609.09158)) | Sep 2026 | Whole-body VLA: language + front and downward RGB → 29-DoF joint action chunks, executed by SONIC | G1. VLA every 0.5 s on an offboard RTX PRO 6000 server; SONIC tracker on the onboard Orin NX at about 200 Hz. | Code promised ([project page](https://tango-vla.github.io/tango-vla.github.io)) | **Watch** |
| **HINT-VLM** ([arXiv 2611.11665](https://arxiv.org/abs/2611.11665)) | Nov 2026 | VLM movability prior plus Gaussian-process correction from push outcomes, for navigating among movable obstacles | G1 with a Livox LiDAR and ZED X camera; VLM on an external RTX 5090 laptop, AGX Orin onboard | Not stated ([project page](https://yzwfromk.github.io/HINT_VLM/)) | **Watch (semi-static obstacles)** |
| **FocusNav** ([arXiv 2601.12790](https://arxiv.org/abs/2601.12790)) | Jan 2026 | Learned humanoid local navigation: waypoint prediction with attention over bird's-eye-view features | G1 with Livox MID-360 and D435i | No code stated | **Watch; possible alternative to MPPI** |
| **HoloMotion v2** ([GitHub](https://github.com/HorizonRobotics/HoloMotion)) | Oct 2026 | Whole-body motion tracking and sparse-to-whole-body teleop (1-point or 5-point from PICO VR) | G1 29-DoF with Orin listed as a deployment target | Yes. G1 checkpoint on Hugging Face; code Apache-2.0, weights license not stated | **Later (Mode 5 teleop data)** |
| **FRoM-W1** ([GitHub](https://github.com/OpenMOSS/FRoM-W1)) | 2026 | Text → human motion → retargeted G1 tracking policies | G1 student policies downloadable | Partly. Code Apache-2.0 | **Reference** |
| **GNM** (General Navigation Model) | 2023 (re-evaluated Mar 2026) | ViNT's smaller predecessor with a MobileNetV2 encoder | In a 2026 real-world test it was more robust than ViNT and NoMaD under distribution shift (see below) | Yes, open weights | **Shadow test, alongside ViNT** |
| **NoMaD** | 2023 (re-evaluated Mar 2026) | ViNT successor with diffusion action head and exploration mode | Same test: more collisions than ViNT, good goal recognition on stairs | Yes, open weights | **Alternative for the shadow test** |
| **GemNav** ([arXiv 2607.06882](https://arxiv.org/abs/2607.06882)) | Jul 2026 | Gemma-4 adapted with LoRA to predict waypoints | Beat ViNT and NoMaD offline (SCAND ADE 0.76 m vs 2.89 m for ViNT), but about 2 Hz on Jetson AGX Thor; tested on Spot, ANYmal D and a rover | No code stated | **Watch** |
| **NavWAM** ([arXiv 2606.13494](https://arxiv.org/abs/2606.13494)) | Jun 2026 | Navigation world-action model on Cosmos Predict2 | 79% real-robot success vs 58% for OmniVLA; about 5 Hz on an RTX PRO 6000; robot used MID-360 + D455 | No code stated | **Watch** |
| **Cosmos 3 Edge** ([model card](https://huggingface.co/nvidia/Cosmos3-Edge)) | 20 Jul 2026 | 4B model: reasoning, image-to-video world prediction, action dynamics | Tested by NVIDIA on Jetson Thor and the 64 GB AGX Orin, not the Orin NX. 32 actions per inference at 15 Hz on Thor. | Yes. OpenMDW 1.1 license | **Later; candidate to replace Cosmos-Reason2-2B on the laptop (VRAM not stated, measure first)** |
| **GR00T N2** | Previewed 16 Mar 2026 | Next GR00T generation, based on DreamZero research | Navigation and locomotion not mentioned | Preview only, stated availability end of 2026 | **Wait** |

**What the 2026 real-world evaluation found** ([arXiv 2603.25937](https://arxiv.org/abs/2603.25937), Spot and a tracked rover with a fisheye camera, Jetson AGX Xavier/Orin):

- **Collisions:** ViNT 0 of 3 in a corridor and 1 of 10 in an office loop; NoMaD 3 of 3 and 2 of 10.
- **Repetitive scenes:** in an arena with similar-looking doors, ViNT stopped 3.09 m from the goal and NoMaD 7.97 m; GNM reached 0.91 m.
- **Out of distribution (snow):** mean final distance GNM 1.12 m, ViNT 9.96 m, NoMaD 10.76 m.
- **Authors' conclusion:** encoder quality mattered more than architecture, and none of the models has real geometric understanding. Use them for route following, never as the collision safety layer.

**Measured on our RTX 5090 laptop (smoke test, added 2026-11-24):** all three load with 0 checkpoint key mismatches. Peak VRAM: GNM 135 MB, ViNT 541 MB, NoMaD 202 MB. Latency p50/p95: GNM 8.0/8.8 ms, ViNT 11.7/12.1 ms, NoMaD 30.6/31.3 ms (8 samples). All are far inside a 4 Hz control budget and leave the 24 GB nearly untouched. These come from a synthetic walk, so they say nothing yet about navigation quality; see [the route test](../../../experiments/vnm_route_test/README.md).

**Balance note (added from the paper audit, 2026-11-24):** these results do not support ranking GNM above ViNT overall. ViNT had fewer office-loop collisions (1/10 vs 5/10 for GNM); GNM was better only in the repetitive-door arena and in snow. Trial counts are small and collisions depend on each platform's own controller. Treat the shadow test, not this paper, as the deciding evidence.

## 9. Papers and models from the navigation paper audit (added 2026-11-24)

Source: [G1 navigation paper audit](./workspace-01a20e49-d39f-7fc0-8719-2c1484423718/G1_navigation_paper_audit.md) in workspace `01a20e49`. Figures below are copied from that audit and have not been re-checked against the papers here, except where marked.

| Paper / model | Audit status | What it is | Evidence on a G1? | Relevance to us | Verdict |
|---|---|---|---|---|---|
| **Caging VLN** ([arXiv 2611.04972](https://arxiv.org/abs/2611.04972)) | Full paper read; existence confirmed in our web check | A VLM/VLA proposes goals; Bézier-parameterized MPPI over a 2D SDF; a discrete exponential barrier function (dEBF) rejects uncertified actions and applies a safe backup | Yes. Large G1 test: 60/60 uncaged trials collided, 0/60 caged. End-to-end tests: success 0.75 kept while collisions fell from 0.33/0.50 to 0 | Almost exactly our planned onboard MPPI + CBF layer, shown on a G1 | **Use now as the design for the safety cage** |
| **RoM-Nav** ([arXiv 2609.19272](https://arxiv.org/abs/2609.19272)) | Full paper read; existence confirmed in our web check | Two-stage RL: navigation trained on a reduced-order model, then transferred to full humanoid dynamics; Poisson safety filter / CBF-QP on planar velocity | Yes. G1 with MID-360 and downward ZED Mini; nav policy 5 Hz, locomotion 50 Hz; routes up to 100 m and 10 m climb; safety filter cut OOD collisions from 2/10 to 0/10 | Strongest candidate for stairs and multi-floor routes to metric goals | **Later (when stairs or multiple floors matter)** |
| **LHNav** (arXiv 2611.12136) | Full paper read per audit; **not found in our web search** | Brain (task plan, arrival check up to 1 Hz) + Cerebellum VLA (~8 Hz, whole-body motion tokens and waypoints) + frozen SONIC decoder at 50 Hz | Small: G1 home tasks, 5 trials per condition; three-destination task 4/5. Long-horizon results mostly in simulation (75.6% task success) | Closest precedent for multi-stop whole-body navigation; supports SONIC (Combination B) | **Watch; confirm the paper exists first** |
| **EgoNav, human-data prior** ([arXiv 2604.00416](https://arxiv.org/abs/2604.00416)) | Full paper read | Trajectory-diffusion prior trained on ~25 km of human walking video, 360° visual memory, frozen DINOv3 features | Yes. 37.5 min, 1,137 m, 96–99% autonomous time; turned away from glass that depth missed. Diffusion runs on a Jetson Thor attached to the Orin NX, about 1.7 Hz. No baseline comparison | Crowd and glass cues | **Later (needs Thor-class compute)** |
| **EgoNav, geometry-aware** ([arXiv 2608.25642](https://arxiv.org/abs/2608.25642)) | Full paper read | Place recognition on a topological map + GNM waypoints + semantic RGB-D traversability + Falco local planner | No. Humanoid upper body on an omnidirectional wheeled base; inference on Orin NX. Real success 73/67/47% at short/medium/long range vs 60/50/33% for PlaceNav+Falco | The pattern of learned waypoints checked by a geometric planner, on our onboard computer class | **Alternative (pattern for Combination D)** |
| **FocusNav** (already in section 8) | Full paper read | — | Yes. 15 trials per configuration on stairs, slopes, obstacles and pedestrians; hardest simulated case 87% vs 64% for the best baseline. Slightly more collisions in one setting because the stability gate favors not falling | Learned local planner for rough terrain | **Unchanged (Watch)** |
| **SAFER-Nav** ([arXiv 2606.11636](https://arxiv.org/abs/2606.11636)) | Full paper read | Adds a segmentation branch to a frozen ViNT-style policy to bias waypoints into free space | No. Small wheeled robots; moving-robot tests 0/10 collisions vs 5/10 and 9/10 for ViNT | Cheap way to make a ViNT shadow candidate less collision-prone | **Alternative for the shadow test** |
| **VISTA** ([arXiv 2606.17294](https://arxiv.org/abs/2606.17294)) | Full paper read | Conditions visual waypoints on recent actions so metric scale stays consistent across speeds and control rates | G1 shown in a figure only; quantitative tests on a tracked rover | Fixes scale mismatch when running ViNT-style models on the G1's gait | **Later (add-on to Combination D)** |
| **X-NavDP** ([arXiv 2607.28560](https://arxiv.org/abs/2607.28560)) | Screened only | RL post-training for NavDP, including G1 | Claimed; not audited | Upgrade path for the NavDP local planner used by Uni-LaViRA | **Watch** |
| **TAPNAV** ([arXiv 2610.10748](https://arxiv.org/abs/2610.10748)) | Screened only | Tactile active perception for G1 navigation | Claimed; not audited | Fallback when vision is degraded | **Reference** |
| **X-Nav** ([arXiv 2611.17598](https://arxiv.org/abs/2611.17598)), **GuideWalk** ([arXiv 2606.10449](https://arxiv.org/abs/2606.10449)), **NavFoM** (ICLR 2026) | Screened only | Long indoor-to-outdoor language missions; unified locomotion and navigation (Kuavo robot); large navigation foundation model run remotely on a 4090/5090 | No | Background for long missions | **Reference** |
| **Whole-body confined-space planning** ([arXiv 2608.10220](https://arxiv.org/abs/2608.10220)) | Abstract only | Whole-body collision and clearance planning | Not audited | Covers what the planar safety filters above do not | **Watch** |

**Audit's architecture summary:** no single paper covers goal selection, social reasoning, biped motion, dynamic obstacles and safety together. It recommends composing a goal layer, a navigation prior, a geometric executor and a safety cage. This matches the recommended stack above.

---

## Recommended stack

Jan's onboard structure, Nav2 for routing, the existing safety layer, and the swap system only when the robot needs semantics or manipulation.

### On the robot (Jetson Orin NX), always running

- **FAST-LIO2** for pose.
- **LV-DOT** for tracking people, plus **YOLOv11-pose** if there is room.
- **Local occupancy + ESDF** for clearance.
- **Geometric MPPI** at 20–30 Hz for local planning around people.
- **Safety:** speed limits fed into MPPI, a CBF filter on velocity commands, the watchdog and the 500 ms buffer.
- **Unitree native locomotion** for walking.

The mapping doc puts FAST-LIO2, YOLOv11-pose and LV-DOT at about 2.2 GB of the Orin NX's 16 GB. MPPI on the Orin NX has not been profiled.

### On the laptop (RTX 5090, 24 GB)

- **Always loaded:** Nav2 route planning at about 1 Hz on the FAST-LIO2 map.
- **Swap slot, one model at a time:** Cosmos-Reason2-2B for Search, GR00T N1.7 for Manipulation.
- **Swap rule:** swap only while standing still, as the V2 orchestrator requires.

The V2 orchestrator puts the Manipulation and Search peaks at 14–16 GB with DINOv3 resident. This stack keeps less loaded, so it should fit with more headroom, but this is unmeasured.

### How it maps to the V2 orchestrator modes

| Mode | What runs |
|---|---|
| 0 Safe/Local | Everything onboard; the laptop is not needed |
| 1 Transit | Onboard stack + Nav2 routes |
| 2 Approach | Transit + GR00T warming up in the swap slot |
| 3 Manipulation | GR00T N1.7 (+ SONIC onboard) |
| 4 Search/Query | Cosmos-Reason2-2B |
| 5 Teach/Teleop | Logging only, for collecting GR00T training data |

### Build order

1. FAST-LIO2, the safety layer and native walking.
2. LV-DOT and onboard MPPI.
3. Nav2 routes. This completes Modes 0 and 1.
4. ViNT shadow test against Nav2.
5. Cosmos-Reason2-2B for finding people (Mode 4).
6. GR00T N1.7 for the flyer handover (Mode 3).

### What would change this

- **The Orin NX cannot hold the MPPI rate:** move MPPI to the laptop, but keep the onboard safety filter and stop behavior.
- **ViNT clearly beats Nav2 in shadow tests:** promote it to route planning, with the same safety layer underneath.
- **Native walking is too imprecise around people:** bring forward ULTRA or Jan's motion policy.
- **Dense crowds break MPPI:** try π0.5 flow-matching routing.

---

## Additional stack combinations (added 2026-11-24)

These are extra options built on the new models in section 8. The recommended stack above stays the baseline; each combination below changes only the parts it names.

### Combination B: Recommended stack + SONIC walking

- **Changes:** SONIC replaces Unitree native locomotion as the onboard walking controller.
- **Why:** G1 checkpoints are downloadable now, it runs at 50 Hz, and NVIDIA's GR00T N1.7 + SONIC workflow on the G1 makes Mode 3 (Manipulation) a supported path instead of a custom integration.
- **Risk:** onboard vs external-PC deployment is not stated on the repository; check that it fits on the Orin NX next to LV-DOT and MPPI.

### Combination C: Recommended stack + OpenBelief-style Search mode

- **Changes:** Mode 4 (Search/Query) uses an open-vocabulary object memory on the RTX 5090, with Nav2 onboard executing the target pose and an RGB-D check on arrival.
- **Why:** OpenBelief-Nav ran this split on a G1 with our LiDAR, camera and laptop GPU.
- **Risk:** code is not released yet; their onboard computer was a Jetson AGX Orin, not the Orin NX.

### Combination D: Learned route following (GNM / ViNT / NoMaD)

- **Changes:** GNM, ViNT and NoMaD all run in shadow mode against Nav2 instead of ViNT alone. The best one can replace Nav2 for routes on recorded paths, with the same onboard MPPI and safety layer underneath.
- **Why:** the 2026 real-world evaluation found GNM more robust than ViNT under distribution shift, and ViNT better than NoMaD on collisions.
- **Risk:** all three struggle with repetitive scenes and none give metric safety.

### Combination E: Cosmos 3 Edge in the swap slot

- **Changes:** Cosmos 3 Edge (4B) replaces Cosmos-Reason2-2B for Mode 4, and could later add short-horizon world prediction.
- **Why:** newer, open weights, and covers reasoning plus world prediction in one model.
- **Risk:** VRAM needs are not published; NVIDIA tested it on Thor and the 64 GB AGX Orin only. Measure on the RTX 5090 first.

### Combination F: Whole-body VLA navigation (TANGO-style)

- **Changes:** a language + RGB VLA on the laptop outputs 29-DoF action chunks every 0.5 s; SONIC tracks them onboard at about 200 Hz; the onboard safety layer still gates motion.
- **Why:** one learned model handles cluttered navigation and body motion together.
- **Risk:** TANGO used an RTX PRO 6000 server GPU, code is not released, and it uses RGB only, with no LiDAR safety. Research track only.

### Combination G: Interactive navigation (HINT-VLM-style)

- **Changes:** adds a movability estimate from a VLM on the RTX 5090, so the robot can push aside light obstacles instead of only avoiding them.
- **Why:** covers the semi-static obstacle scenario (curriculum level 5) with the same laptop/robot split.
- **Risk:** no released code; pushing objects near people needs extra safety rules.

### Combination H: Learned local planner (FocusNav-style)

- **Changes:** a learned waypoint planner over LiDAR and depth features replaces onboard MPPI.
- **Why:** shown on a G1 with our sensors.
- **Risk:** no code, and onboard compute and rate are not stated. Only worth it if MPPI proves too slow or too jerky.

### Combination I: Teleop data collection with HoloMotion v2

- **Changes:** Mode 5 (Teach/Teleop) uses HoloMotion v2 with PICO VR for 1-point or 5-point whole-body teleop.
- **Why:** a downloadable G1 29-DoF checkpoint; produces demonstrations for GR00T fine-tuning.
- **Risk:** weights license not stated.

### Additional build steps

These extend the build order above without replacing it:

7. Try SONIC on the G1 (Combination B).
8. Add GNM and NoMaD to the ViNT shadow test (Combination D).
9. Measure Cosmos 3 Edge VRAM and latency on the RTX 5090 (Combination E).
10. Revisit Combinations C, F, G and H when their code is released.

### More combinations from the paper audit (added 2026-11-24)

These build on section 9. Earlier combinations are unchanged.

#### Combination J: Recommended stack with a Caging-VLN-style safety cage

- **Changes:** the onboard safety layer becomes Bézier-parameterized MPPI over a 2D SDF, with a discrete exponential barrier function check on several footprint points and a safe backup action. Every proposer (Nav2, ViNT, a VLM) only suggests goals; the cage decides what executes.
- **Why:** shown on a G1, removing all collisions in 60 caged trials with no loss in success rate.
- **Risk:** the guarantee assumes a correct planar model, a current SDF and exact execution. Latency, tracking error, arm swing, stairs and unseen geometry (thin wires, glass) are not covered. Keep the watchdog and stop behavior.

#### Combination K: RoM-Nav for stairs and multiple floors

- **Changes:** for multi-floor routes, a RoM-Nav-style learned navigation policy (5 Hz, LiDAR + goal) with its CBF-QP velocity filter replaces Nav2 + MPPI; native walking or SONIC stays underneath at 50 Hz.
- **Why:** the strongest G1 evidence for stairs and long routes (up to 100 m and 10 m of climb).
- **Risk:** needs accurate metric goals and a separate map/relocalization system; misses glass; the safety filter is planar. Training took under 45 hours on one H100, so it needs the HPC cluster.

#### Combination L: Long-horizon multi-stop navigation (LHNav-style)

- **Changes:** a task-manager VLM checks arrival at up to 1 Hz; a VLA outputs whole-body motion tokens at about 8 Hz; SONIC decodes them at 50 Hz; Combination J's cage sits underneath.
- **Why:** visiting several destinations in order, such as people at a fair, with natural whole-body motion.
- **Risk:** paper existence not yet confirmed by us; real G1 evidence is small; no independent safety guarantee of its own.

#### Combination M: Learned waypoints checked by a geometric planner (geometry-aware EgoNav pattern)

- **Changes:** GNM (or ViNT) proposes a waypoint; semantic RGB-D traversability and clearance scoring pick a safe candidate; a local planner (Falco in the paper, our MPPI here) executes it.
- **Why:** shown to beat a learned-only baseline, with inference on an Orin NX-class computer. A safer route to promoting the Combination D winner.
- **Risk:** tested on a wheeled base, not a biped; needs a pre-collected route; obstacle handling is reactive only.

#### Combination N: Human-data navigation prior for crowds and glass (EgoNav human-data)

- **Changes:** a diffusion trajectory prior trained on human walking video proposes paths, with DINOv3 features for glass cues; the cage executes.
- **Why:** the only G1 evidence here for avoiding glass that depth sensing misses.
- **Risk:** needs a Jetson Thor (or the tethered laptop) and runs at about 1.7 Hz; no baseline comparison in the paper.

#### Combination O: Safer, scale-aware visual navigation in the shadow test

- **Changes:** add SAFER-Nav's segmentation branch and VISTA's action-history conditioning to the ViNT/GNM candidates in Combination D.
- **Why:** fewer collisions (SAFER-Nav) and consistent step scale across walking speeds (VISTA).
- **Risk:** both mainly tested on wheeled or tracked robots.

### More build steps

11. Implement the safety cage from Combination J before trusting any learned planner.
12. Add Combination M as the promotion route for whichever model wins the shadow test.
13. Confirm LHNav exists, then reconsider Combination L for the fair scenario.
14. Revisit Combination K when the robot needs stairs or multiple floors.

---

## Benchmarks (added 2026-11-24)

No single benchmark covers a G1 walking among people with Nav2 and MPPI, so combine these.

| Benchmark | What it tests | Fit for us | Code |
|---|---|---|---|
| **Own real-world route test**, modeled on [arXiv 2603.25937](https://arxiv.org/abs/2603.25937) | Topological route following in several environments; collisions and final goal distance | Fairest comparison of Nav2, GNM, ViNT and NoMaD on our robot | Their dataset and code are promised |
| **NavIsaacLab** ([arXiv 2606.26265](https://arxiv.org/abs/2606.26265)) | Social point-goal navigation among realistic simulated crowds in Isaac Lab | Matches our Isaac tooling and crowd scenarios. G1 support not stated. | Not stated |
| **DPed-VLN** ([arXiv 2609.21504](https://arxiv.org/abs/2609.21504)) | Language navigation with 1–6 moving pedestrians in Habitat 3.0; metrics SR, SPL, STL, human collision rate, personal-space compliance | Best ready-to-use test for Search mode with people around | [Public](https://github.com/tju-dhj/DPedVLN) |
| **HumanoidVLN** ([arXiv 2608.12860](https://arxiv.org/abs/2608.12860)) | Language navigation in Isaac Sim with the G1 as a supported robot; metrics SR, OS, NE, SPL, nDTW, fall rate. 933 episodes. Static scenes, no pedestrians. | Only benchmark with the G1 built in. Sim-to-real pilot on a G1: navigation errors correlated r = 0.935. | Promised on acceptance |
| **SocNavBench** ([arXiv 2103.00047](https://arxiv.org/abs/2103.00047)) | Social navigation with real pedestrian trajectories; path quality, motion quality, pedestrian disruption | Older reference metric suite | Public (older) |

**Metrics to report everywhere:** success rate, SPL, collisions with people and with objects, personal-space intrusion, fall rate, time, path length, and jerk. There is no agreed social-navigation protocol, so fix thresholds such as personal-space distance once and keep them.

### More benchmarks from the benchmark review (added 2026-11-24)

Source: [navigation and social-safety benchmark review](./workspace-01a20e49-d39f-7fc0-8719-2c1484423718/navigation_social_benchmarks_review.md) in workspace `01a20e49`. Not re-checked here.

| Benchmark | What it tests | G1 or real-world evidence | Use it for |
|---|---|---|---|
| **"What the Elevation Map Cannot See"** ([arXiv 2610.07396](https://arxiv.org/abs/2610.07396)) | Visible, ambiguous and invisible floor hazards; disturbances; falls; drift between commanded and actual motion | G1 locomotion tested on real floors (5 trials per method per surface); the navigation part is simulated | G1 hazard and robustness tests |
| **VLN-PE** ([arXiv 2507.13019](https://arxiv.org/abs/2507.13019)) | Physically executed language navigation across robot bodies and camera heights, in Isaac Sim | Supports H1 and G1 | Checking how our camera height and gait affect navigation models |
| **HA-VLN** ([arXiv 2503.14229](https://arxiv.org/abs/2503.14229), [project](https://ha-vln-project.vercel.app/)) | Language navigation among multiple moving people; personal-space and collision metrics | Real trials with 2–4 volunteers, but on a Go2 quadruped | Social layer of Search mode; a real-robot trial protocol |
| **SidewalkBench** ([arXiv 2606.16953](https://arxiv.org/abs/2606.16953)) | Sidewalks, crossings, gestures, long routes with reactive pedestrians | Not humanoid | Only if the G1 will be used outdoors on sidewalks |
| **OmniNavBench** ([arXiv 2605.09441](https://arxiv.org/abs/2605.09441), [code](https://github.com/AutoLab-SAI-SJTU/OmniNavBench)) | Several navigation skills in one episode (PointNav, VLN, ObjectNav, SocialNav, human following) | H1 in simulation, very low baseline success and high fall rates | Stress-testing mode switching |
| **NavVerse** ([arXiv 2607.19695](https://arxiv.org/abs/2607.19695)) | Indoor, outdoor and indoor-to-outdoor transitions | Spot and Turtlebot; humanoids not tested | Building-to-street routes |
| **VLNVerse** ([arXiv 2512.19021](https://arxiv.org/abs/2512.19021)), **LHPR-VLN** ([arXiv 2412.09082](https://arxiv.org/abs/2412.09082)) | Broad language-navigation task coverage; long-horizon multi-step instructions | Simulation only | Long multi-stop instructions |
| **RESONATE** ([arXiv 2611.02937](https://arxiv.org/abs/2611.02937)) | Real-world social navigation: 8 scenarios × 8 controllers × 5 repetitions = 320 runs, Vicon ground truth, participant ratings | Wheeled Jackal | Template for our own real G1 trials with people |
| **PEDS** ([project](https://pedsral26.github.io/)), **PopNavShift** ([arXiv 2609.21838](https://arxiv.org/abs/2609.21838)) | Whether policy rankings change with the pedestrian simulation model | Simulation; PopNavShift found pedestrian-burden rankings reverse in about 22–26% of comparisons | Running every social test with more than one crowd model |
| **HuNavSim 2.0** ([code](https://github.com/robotics-upo/hunav_sim)), **SEAN 2.0**, **Arena-Bench** ([code](https://github.com/ignc-research/arena-rosnav)) | ROS-based crowd simulation and planner comparison | Mobile robots | Regression tests for Nav2/MPPI in ROS 2 |
| **HumanoidBench** ([arXiv 2403.10506](https://arxiv.org/abs/2403.10506)) | Simulated humanoid locomotion and manipulation | No navigation | Walking-controller comparisons only |

**Layered battery the review recommends:**

1. **Route and language navigation:** HumanoidVLN, cross-checked with VLN-PE. Report G1 results separately.
2. **Biped hazards:** the hazard taxonomy from "What the Elevation Map Cannot See", plus our own push, stair and sensor-fault tests.
3. **People:** HA-VLN or DPed-VLN, run with more than one pedestrian model (PEDS/PopNavShift style).
4. **Composite and long-horizon tasks:** selected OmniNavBench and LHPR-VLN tasks.
5. **Real G1 trials with people:** staged from empty corridors to denser crowds, following the RESONATE protocol, with consenting participants, a safety stop and predefined abort rules.

**Extra reporting items from the review** (in addition to the metrics above):

- Subgoal completion, not only overall success.
- Contacts split into human, environment and hidden-hazard contacts.
- Fall and recovery rate.
- The distribution of distances to people, near misses and yielding, not only a collision flag.
- Commanded versus actual pose and heading error.
- Results broken down by crowd density, scene split and perturbation level.
- The pedestrian model used, trial counts, participant exposure and safety interventions.

---

## Conflicts still open in the docs

- **Planner:** the launchpad shows latent MPPI (architecture page), A\* (swap page) and MPPI on the RTX 5090 (block diagram). This note picks geometric MPPI onboard.
- **VLM:** the launchpad and block diagram use Cosmos 3 Nano, while the V2 orchestrator rejects it for VRAM and keeps Cosmos-Reason2-2B.
- **Whole-body control rate:** the launchpad says 500 Hz; the V2 orchestrator and Jan's proposal say 50 Hz.
- **V3 VRAM total:** the swap page shows both 18.1 GB and 21.1 GB.

### Caveats found in the 2026-11-24 web check

- **Cosmos-Reason2-2B memory:** NVIDIA's [model card](https://huggingface.co/nvidia/Cosmos-Reason2-2B) says it requires at least 24 GB of GPU memory and was tested at BF16 only. The 4-bit W4A16 version our swap plan assumes is not NVIDIA-validated. Measure it on the RTX 5090 before relying on it.
- **GR00T N1.7 backbone:** NVIDIA's pages do not say GR00T N1.7 uses Cosmos-Reason2-2B as its backbone; only a third-party blog does. The V2 orchestrator's first reason for choosing Cosmos-Reason2-2B rests on that link.
- **Onboard computer in papers:** most new G1 papers use a Jetson AGX Orin (64 GB) or Thor onboard, not our Orin NX (16 GB). Their onboard parts may not fit as-is.
- **Planar safety guarantees (from the paper audit):** Caging VLN's and RoM-Nav's safety filters reason about a flat footprint and planar velocity. Neither proves whole-body balance, foot clearance or arm clearance on the G1.
- **LHNav not confirmed:** the audit says it read LHNav (arXiv 2611.12136) in full, but our web search did not find it. Check the arXiv listing before relying on it.

## Sources

- [Feasibility review](./FEASIBILITY_REVIEW.md), [literature improvements](./LITERATURE_IMPROVEMENTS.md), [revised architecture](./REVISED_ARCHITECTURE.md), [compute budget](./COMPUTE_BUDGET_PROFILED.md)
- [V2 orchestrator](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/DYNAMIC_ORCHESTRATION_ARCHITECTURE.md), [architecture variations](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/ARCHITECTURE_VARIATIONS.md), [LLM and VLM roles](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/LLM_AND_VLM_ROLES.md), [VRAM measurements](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/VRAM_MEASUREMENTS.md)
- [Curriculum of complexity](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/2026_ARCHITECTURE_JUSTIFICATION_CURRICULUM.md), [mapping and dynamic SLAM](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/2026_ENVIRONMENT_MAPPING_DYNAMIC_SLAM.md), [3D scene review](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/3D_SCENE_REPRESENTATION_REVIEW.md), [Uni-LaViRA analysis](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/UNI_LAVIRA_ANALYSIS.md), [state of the art](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/STATE_OF_THE_ART_2026.md)
- [Launchpad](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/index.html) and its pages
- [Jan's proposal slides](./workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/PRESENTATION%20%282%29.pdf)

**Web sources (checked 2026-11-24):**

- Navigation: [OpenBelief-Nav](https://arxiv.org/abs/2608.13923), [TANGO](https://arxiv.org/abs/2609.09158), [HINT-VLM](https://arxiv.org/abs/2611.11665), [FocusNav](https://arxiv.org/abs/2601.12790), [Can Vision Foundation Models Navigate?](https://arxiv.org/abs/2603.25937), [NavWAM](https://arxiv.org/abs/2606.13494), [GemNav](https://arxiv.org/abs/2607.06882)
- Whole-body control: [GR00T-WholeBodyControl (SONIC)](https://github.com/NVlabs/GR00T-WholeBodyControl), [HoloMotion](https://github.com/HorizonRobotics/HoloMotion), [FRoM-W1](https://github.com/OpenMOSS/FRoM-W1)
- NVIDIA: [Cosmos 3 Edge model card](https://huggingface.co/nvidia/Cosmos3-Edge), [Cosmos 3 Edge announcement](https://huggingface.co/blog/nvidia/cosmos3edge), [Cosmos-Reason2-2B model card](https://huggingface.co/nvidia/Cosmos-Reason2-2B), [GTC 2026 announcement (GR00T N1.7, GR00T N2)](https://nvidianews.nvidia.com/news/nvidia-expands-open-model-families-to-power-the-next-wave-of-agentic-physical-and-healthcare-ai)
- Benchmarks: [HumanoidVLN](https://arxiv.org/abs/2608.12860), [NavIsaacLab](https://arxiv.org/abs/2606.26265), [DPed-VLN](https://arxiv.org/abs/2609.21504), [DPed-VLN code](https://github.com/tju-dhj/DPedVLN), [SocNavBench](https://arxiv.org/abs/2103.00047)
- Workspace `01a20e49` (added 2026-11-24): [G1 navigation paper audit](./workspace-01a20e49-d39f-7fc0-8719-2c1484423718/G1_navigation_paper_audit.md), [navigation and social-safety benchmark review](./workspace-01a20e49-d39f-7fc0-8719-2c1484423718/navigation_social_benchmarks_review.md)
