# Humanoid Parkour Learning

**Paper:** [arXiv:2406.10759](https://arxiv.org/abs/2406.10759)  
**Venue:** 8th Annual Conference on Robot Learning (CoRL 2024)  
**Authors:** Ziwen Zhuang, Shenzhe Yao, Hang Zhao (Shanghai Qi Zhi Institute, ShanghaiTech University, Tsinghua University)  
**Core Domain:** Vision-Based Whole-Body Control, Reinforcement Learning, Locomotion Skills

---

## 🔬 Core Contribution

A unified, end-to-end vision-based reinforcement learning framework that enables humanoid robots to perform diverse parkour maneuvers — **jumping, leaping, climbing, and running** — **without any motion priors or reference trajectories**. The key innovation is using **fractal noise** on terrain during simulation to naturally encourage foot-raising behaviors, bypassing the need for manually engineered "feet air time" rewards or motion capture data.

**Performance:**
- Jump onto **0.42m** platforms
- Leap over **0.8m** gaps
- Run at **1.8 m/s** outdoors
- 10 types of human-capable terrains evaluated

## 🛠 Relevant Mechanisms for G1-JEPA

- **Fractal Noise Terrain Curriculum:** During PPO training in Isaac Sim, the terrain height is perturbed with fractal noise (Perlin-like, multi-octave). This forces the policy to learn natural foot-raising and obstacle negotiation without hand-designed reward terms for "lift foot higher." Directly applicable to our MPPI training pipeline — replaces complex reward engineering for locomotion skills.
- **3-Stage Distillation Pipeline:**
  1. **Stage 1 — Walking:** Train a basic walking policy with fractal noise terrain.
  2. **Stage 2 — Oracle Parkour:** Train a policy with access to ground-truth terrain heightmap (privileged information). This oracle achieves expert-level performance.
  3. **Stage 3 — Vision Student:** Distill the oracle into a student policy using **DAgger** that uses only onboard depth camera images (Intel RealSense D435i — same camera as our G1!).
- **CPU-Only Deployment:** The final student policy runs **onboard** on a 12-core Intel i7 CPU (two Python processes communicating via ROS 2 + Cyclone DDS — one for the CNN vision encoder, one for the control loop). No GPU needed. This is directly relevant to our V7 (Minimal Onboard — Distilled) architecture.
- **Domain Randomization for D435i:** The authors specifically simulate the noise characteristics of the Intel RealSense D435i during training, enabling zero-shot sim-to-real transfer. Our G1 uses the same camera — their sensor noise model is directly reusable.
- **GRU + MLP Actor:** The oracle policy uses a GRU (recurrent) + MLP architecture. The vision student replaces the oracle's terrain heightmap input with a CNN depth encoder but keeps the same recurrent actor. This is architecturally similar to our MPPI planner's trajectory evaluation network.

## 🔗 Interlinks to Project Components

- [x] **Latent Planner / MPPI:** The fractal noise terrain curriculum could augment our MPPI training to generate more agile trajectory samples without complex reward engineering. The GRU-based actor architecture is a reference for our action-conditioned predictor.
- [x] **Predictive Loop (V-JEPA 2):** The paper's world model is implicit (PPO value function + GRU memory), not explicit like V-JEPA 2. However, the skill distillation approach (oracle → student) mirrors our V7 (Cosmos/GR00T teacher → distilled student) strategy.
- [x] **V7 Minimal Onboard:** This paper proves that a vision-based locomotion policy can run **onboard a CPU** (no GPU) at sufficient frequency for real-time control. Our V7 distilled student targets Jetson Orin NX (100 TOPS) — this paper shows a CPU-only deployment is feasible as a baseline.
- [x] **Safety Layer (CBF):** The paper does not include explicit safety filters — it relies on the policy's learned robustness. For our G1, we'd add our CBF safety filter as an outer loop, which is strictly safer.
- [x] **Hardware Ops:** The D435i depth camera noise model is directly reusable. The paper runs on Unitree H1 — same manufacturer as our G1, meaning the motor interface, URDF, and joint limits are likely compatible or easily adaptable.

## 🚀 Actionable Integration Plan

1. **Adopt fractal noise terrain for MPPI training:** Modify our Isaac Lab training environment to add multi-octave Perlin noise to terrain height. This is a drop-in change — no reward function modifications needed for basic locomotion.
2. **Reuse D435i sensor noise model:** The paper's domain randomization parameters for the Intel RealSense D435i are published. Integrate these into our sim-to-real pipeline to improve zero-shot transfer quality.
3. **Benchmark CPU-only deployment:** As a baseline for V7, test whether a distilled student policy (CNN + GRU + MLP, ~5–10M params) can run at >10 Hz on our Jetson Orin NX CPU cores. The paper runs on an Intel i7 — Orin's ARM cores should be comparable or better.
4. **Consider DAgger for V7 distillation:** The paper's 3-stage pipeline (walking → oracle → DAgger student) is a proven recipe. Our V7 currently assumes behavior cloning — DAgger could improve sim-to-real robustness by iteratively collecting on-policy data from the student.
5. **Evaluate parkour skills on G1:** The G1 is smaller (130cm / 35kg vs H1's 180cm / 50kg) but has similar DoF and motor capabilities. Jump height and gap distance would scale down but the methodology transfers directly.
