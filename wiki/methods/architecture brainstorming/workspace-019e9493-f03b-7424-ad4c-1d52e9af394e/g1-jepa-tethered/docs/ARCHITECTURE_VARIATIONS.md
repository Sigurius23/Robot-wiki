# G1 Pipeline Architecture Variations

> **📋 VRAM numbers:** All VRAM and model size figures in this document reference [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md) (canonical source) and [VRAM_QUICKREF.md](./VRAM_QUICKREF.md) (quick lookup). When in doubt, VRAM_MEASUREMENTS.md is authoritative.

**Date:** June 9, 2026
**Purpose:** Explore all logical ways to structure the G1's perception→planning→control pipeline using Cosmos 3, GR00T, VLAs, JEPA, and our unique components. These are variations on the existing architecture, not replacements.

**Hardware Reference:**
- **RTX 5090 (24GB)** — Offboard laptop via Gigabit Ethernet
- **Jetson Orin NX (16GB)** — Onboard the G1
- **HPC Cluster** — Batch-scheduled, training only, no real-time

**Our Unique Components (present in all variations):**
- 4D Voxel Latent Memory (blind spot object permanence)
- Tether-aware planning (yaw penalty + link-loss buffer)
- Acoustic-JEPA (audio hazard detection)
- CBF safety filter + WBC (500Hz reactive)

---

## Variation 1: Pure JEPA — The Baseline

**Philosophy:** Self-supervised world model predicts latent futures. MPPI samples trajectories. No foundation models.

```
┌──────────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                                   │
│                                                                       │
│  ┌─── SEMANTIC LOOP (0.5–1 Hz) ──────────────────────────────────┐  │
│  │  DINOv3 ──→ Slot Attention ──→ VL-JEPA                        │  │
│  │  (segments)   (object slots)    (language grounding)           │  │
│  │  + 3D Gaussian Splatting (lab digital twin)                    │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ object slots + text goals                │
│  ┌─── 4D PREDICTIVE LOOP (5–40 Hz) ──────────────────────────────┐  │
│  │  MinkowskiNet ──→ VICReg ──→ 4D Neural Voxel Splatting        │  │
│  │  (sparse 4D)      (contrast)   (dynamic scene)                 │  │
│  │                           │                                     │  │
│  │  V-JEPA 2 ──→ WorldRFT ──→ Tether-Aware MPPI (1024 samples)   │  │
│  │  (predict)     (RL fine)     (trajectory optimization)          │  │
│  │                           │                                     │  │
│  │  ┌────────────────────────┐                                    │  │
│  │  │ 4D Voxel Latent Memory │ ← Persists across timesteps       │  │
│  │  │ • Rearward blind spots │                                    │  │
│  │  │ • Uncertainty damping  │                                    │  │
│  │  └────────────────────────┘                                    │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ joint targets @ 40Hz                     │
└───────────────────────────┼──────────────────────────────────────────┘
                            │ Gigabit Ethernet
┌───────────────────────────▼──────────────────────────────────────────┐
│ Jetson Orin NX (Onboard)                                              │
│                                                                       │
│  ┌─── REACTIVE LOOP (500 Hz) ───────────────────────────────────┐   │
│  │  FAST-LIO2 ──→ Proprioceptive CBF ──→ Link-Loss Buffer       │   │
│  │  (odometry)     (safety filter)        (500ms decay)          │   │
│  │                           │                                     │   │
│  │  Whole-Body Controller (WBC)                                   │   │
│  │  • Inverse kinematics/dynamics                                 │   │
│  │  • Joint limit enforcement                                     │   │
│  │  • 43 DoF motor commands via EtherCAT                          │   │
│  └────────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  Sensors: Livox MID-360 → Intel RealSense D435i → IMU → Encoders    │
└──────────────────────────────────────────────────────────────────────┘
```

> **⚠️ VRAM CORRECTION (June 2026):** The diagram above shows ALL V1 components simultaneously loaded (~33 GB BF16) — this is the worst case. **Standard JEPA** (encoder + predictor + MPPI + Voxel) uses only ~12 GB and fits easily on any 24 GB GPU — matching published papers and community reports. **V-JEPA 2.1 ViT-G/16 (2B, ~10–12 GB BF16) + MPPI + Voxel = ~15–17 GB BF16** — fits any 24 GB GPU for the best-quality standard JEPA. **Our V1 with sequential execution** (Semantic loop runs → unloads → Predictive loop runs) fits at INT8 (~22.6 GB ✅) but not at BF16 (24.8 GB > 24 GB). With 10cm MinkowskiNet voxels: ~18.6 GB INT8 ✅ / ~20.8 GB BF16 ✅. See [VRAM_MEASUREMENTS.md §6](./VRAM_MEASUREMENTS.md#6-corrected-vram-budgets-per-variation).

> **💡 V-JEPA 2 has 5 model sizes.** Our docs assume ViT-g/16 (1B, ~7.3 GB BF16) — the community standard for RTX 3090/4090. For smaller GPUs: ViT-L/16 (300M, ~3.5 GB BF16) fits RTX 3060 12GB. ViT-G/16 (2B, ~10–12 GB BF16) fits comfortably on any 24 GB GPU. See [VRAM_MEASUREMENTS.md §2](./VRAM_MEASUREMENTS.md#2-v-jepa-2--video-prediction-world-model) for the full variant table.

---

## Variation 2: Cosmos 3-Centric

**Philosophy:** A single Cosmos 3 Nano model replaces the entire Semantic + Predictive loop. World understanding and action generation in one model.

```
┌──────────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                                   │
│                                                                       │
│  ┌─── COSMOS 3 NANO (16B, NVFP4) ───────────────────────────────┐   │
│  │                                                                │   │
│  │  ┌─────────────────┐     ┌──────────────────┐                │   │
│  │  │ REASONER Tower  │←───→│ GENERATOR Tower   │                │   │
│  │  │ (Autoregressive)│Joint│ (Diffusion)       │                │   │
│  │  │                 │Attn │                    │                │   │
│  │  │ • Scene caption │     │ • Text→Video (SDG) │                │   │
│  │  │ • Object ground │     │ • Image→Video      │                │   │
│  │  │ • Task planning │     │ • Forward Dynamics │                │   │
│  │  │ • Safety check  │     │ • Policy (29D act) │ ← 0.1–1 Hz    │   │
│  │  └────────┬────────┘     └────────┬───────────┘                │   │
│  │           │ text goals            │ video + action chunk       │   │
│  └───────────┼───────────────────────┼────────────────────────────┘   │
│              │                       │                                │
│  ┌───────────▼───────────────────────▼────────────────────────────┐  │
│  │ 4D Voxel Latent Memory + Action Adapter                        │  │
│  │ • Persists Cosmos outputs between calls                        │  │
│  │ • Remaps 29D AgiBot → 43D G1 DoF                               │  │
│  │ • Denormalizes + clamps to G1 limits                           │  │
│  │ • Tether yaw penalty on interpolated trajectory                │  │
│  │ • Interpolates 50-timestep chunk → 40Hz stream                 │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ 43D joint targets @ 40Hz                 │
└───────────────────────────┼──────────────────────────────────────────┘
                            │ Gigabit Ethernet
┌───────────────────────────▼──────────────────────────────────────────┐
│ Jetson Orin NX (Onboard)                                              │
│                                                                       │
│  ┌─── REACTIVE LOOP (500 Hz) ───────────────────────────────────┐   │
│  │  WBC · CBF · Link-Loss Buffer · FAST-LIO2 · IMU              │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

**What changes from baseline:** DINO, Slot Attention, VL-JEPA, V-JEPA 2, MinkowskiNet, VICReg, WorldRFT — all gone. Replaced by a single Cosmos 3 Nano.
**What stays:** 4D Voxel Memory, Action Adapter, WBC, CBF, tether safety, Acoustic-JEPA.

> **💡 V-JEPA 2 has 5 model sizes.** Our docs assume ViT-g/16 (1B, ~7.3 GB BF16) — the community standard for RTX 3090/4090. For smaller GPUs: ViT-L/16 (300M, ~3.5 GB BF16) fits RTX 3060 12GB. ViT-G/16 (2B, ~10–12 GB BF16) fits comfortably on any 24 GB GPU. See [VRAM_MEASUREMENTS.md §2](./VRAM_MEASUREMENTS.md#2-v-jepa-2--video-prediction-world-model).

**Pros:** Drastically simpler. Fewer models to maintain. NVIDIA-supported.
**Cons:** Latency (~1–30s per Cosmos call). Action mode still in PR review. 29D→43D remapping needed.
**When to use:** After Cosmos 3 action mode is stable. Good migration target.

---

## Variation 3: GR00T N1-Centric

**Philosophy:** GR00T N1 as the primary VLA brain. Dual-system architecture maps naturally to our loop hierarchy.

```
┌──────────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                                   │
│                                                                       │
│  ┌─── GR00T N1 ──────────────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  ┌─────────────────────┐     ┌──────────────────────┐        │  │
│  │  │ SYSTEM 2 (Slow)     │     │ SYSTEM 1 (Fast)       │        │  │
│  │  │ Deliberative Reason │────→│ Reflexive Control    │        │  │
│  │  │                     │     │                       │        │  │
│  │  │ • Scene understand  │     │ • Action generation   │        │  │
│  │  │ • Task decomposition│     │ • 20–40 Hz output     │        │  │
│  │  │ • Goal selection    │     │ • Smooth trajectories │        │  │
│  │  │ 0.5–2 Hz            │     │                       │        │  │
│  │  └─────────────────────┘     └──────────┬────────────┘        │  │
│  │                                         │                      │  │
│  │  Input: Camera + text command           │ action tokens        │  │
│  │  Training: Isaac Sim + teleop data      │                      │  │
│  └─────────────────────────────────────────┼──────────────────────┘  │
│                                            │                         │
│  ┌─────────────────────────────────────────▼──────────────────────┐  │
│  │ 4D Voxel Latent Memory                                         │  │
│  │ • Persists GR00T's scene understanding between reasoning cycles│  │
│  │ • Rearward blind spot queries during locomotion               │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ refined action stream @ 40Hz             │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│ Jetson Orin NX — WBC · CBF · FAST-LIO2 · Tether Safety               │
└──────────────────────────────────────────────────────────────────────┘
```

**What changes from baseline:** The entire Semantic + Predictive stack replaced by GR00T N1.
**What stays:** 4D Voxel Memory, WBC, CBF, tether safety.
**Pros:** Purpose-built for humanoid control. System 1/2 split maps to our hierarchy. G1 explicitly supported in Isaac GR00T.
**Cons:** Less capable world modeling than Cosmos (no video generation). Training requires teleop data.
**When to use:** When we want a mature, NVIDIA-supported VLA with proven sim-to-real.

---

## Variation 4: Cosmos 3 + GR00T N1 Hybrid

**Philosophy:** Cosmos 3 does world understanding and goal generation. GR00T N1 translates goals to motor actions. NVIDIA's intended complementary design.

```
┌──────────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                                   │
│                                                                       │
│  ┌─── COSMOS 3 (World Model) ────────────────────────────────────┐  │
│  │  REASONER: "What's in the scene? What's the goal?"             │  │
│  │  GENERATOR: "Here's what should happen" (video prediction)     │  │
│  │  Output: text goals + task-space targets + predicted video     │  │
│  │  Frequency: 0.1–0.5 Hz                                         │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ goals + task-space waypoints             │
│  ┌─── GR00T N1 (Action Model) ───────────────────────────────────┐  │
│  │  SYSTEM 2: Refines goal into sub-tasks                        │  │
│  │  SYSTEM 1: Generates 29D action chunks @ 20–40 Hz             │  │
│  │  Output: smooth action trajectory                             │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ action chunks                           │
│  ┌─── 4D Voxel Memory + Action Adapter ──────────────────────────┐  │
│  │  Persists Cosmos scene understanding                          │  │
│  │  Remaps 29D → 43D, denormalizes, clamps                       │  │
│  │  Tether yaw penalty                                           │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ 43D @ 40Hz                              │
└───────────────────────────┼──────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│ Jetson Orin NX — WBC · CBF · FAST-LIO2 · Tether Safety               │
└──────────────────────────────────────────────────────────────────────┘

                       ┌──────────────────────┐
                       │ HPC Cluster          │
                       │ Cosmos 3 Super (64B) │
                       │ → Synthetic data gen │
                       │ → GR00T Dream data   │
                       │ → Batch fine-tuning  │
                       └──────────────────────┘
```

**What changes:** Both Cosmos and GR00T replace JEPA stack. They work as a pipeline.
**Pros:** Best of both — Cosmos for understanding, GR00T for acting. Full NVIDIA ecosystem. HPC for scalable training.
**Cons:** Most complex integration. Two large models to run. Highest VRAM pressure.
**When to use:** Production target. When both Cosmos and GR00T are mature and we have HPC access.

---

## Variation 5: Cosmos 3 (Semantic) + V-JEPA 2 (Predictive) Hybrid

**Philosophy:** Cosmos 3 handles scene understanding at low frequency. V-JEPA 2 + MPPI handles 40Hz local planning. Best of foundation model + fast world model.

```
┌──────────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                                   │
│                                                                       │
│  ┌─── SEMANTIC: Cosmos 3 Reasoner (0.1–1 Hz) ───────────────────┐  │
│  │  Image → "Table with red cup 30cm left, path clear to kitchen"│  │
│  │  Task → "Pick up red cup" → goal embedding                    │  │
│  │  Output: language goals + scene graph + goal embedding         │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ goal embedding + semantic context        │
│  ┌─── PREDICTIVE: V-JEPA 2 + MPPI (5–40 Hz) ────────────────────┐  │
│  │  V-JEPA 2-AC: Action-conditioned latent prediction            │  │
│  │  MPPI: 1024 trajectory samples, minimize dist to goal         │  │
│  │  WorldRFT: RL-fine-tuned safety awareness                     │  │
│  │  MinkowskiNet: Efficient 4D processing                        │  │
│  │  Output: 43D joint trajectory @ 40Hz                          │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │                                         │
│  ┌─── 4D Voxel Latent Memory ────────────────────────────────────┐  │
│  │  Stores Cosmos scene graph as persistent spatial memory       │  │
│  │  Query rearward voxels during backward steps                  │  │
│  │  Uncertainty-triggered damping                                │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│ Jetson Orin NX — WBC · CBF · FAST-LIO2 · Tether Safety               │
└──────────────────────────────────────────────────────────────────────┘
```

**What changes:** Cosmos replaces DINO + Slot + VL-JEPA (Semantic only). V-JEPA 2 + MPPI stays for Predictive.
**Pros:** Cosmos for high-quality scene understanding. JEPA for fast 40Hz prediction. Pragmatic migration — only replace the slowest loop.
**Cons:** Still two different model families to maintain. V-JEPA 2 isn't NVIDIA-optimized.
**When to use:** Gradual migration. Start by replacing Semantic loop, keep Predictive loop for speed.

---

## Variation 6: π0 VLA + JEPA World Model

**Philosophy:** PI Zero's flow matching for smooth continuous action generation, combined with JEPA for world state prediction. Best of open VLA + self-supervised world model.

```
┌──────────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                                   │
│                                                                       │
│  ┌─── SEMANTIC: Cosmos 3 Reasoner OR DINO + VL-JEPA ────────────┐  │
│  │  Task: "Pick up the red cup and place it on the blue plate"    │  │
│  │  Output: task instruction + goal image/scene                   │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │                                         │
│  ┌─── ACTION: π0 Flow Matching VLA ──────────────────────────────┐  │
│  │  Input: camera image + task instruction                        │  │
│  │  Architecture: 3B VLM backbone + flow matching action head     │  │
│  │  Output: continuous action chunks @ 50 Hz                      │  │
│  │  Fine-tuned on: G1 teleoperation + Open X-Embodiment           │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ actions                                  │
│  ┌─── WORLD STATE: V-JEPA 2 ─────────────────────────────────────┐  │
│  │  Predicts future latent states for safety verification          │  │
│  │  "Will this action cause a collision?"                         │  │
│  │  Energy-based constraint check on π0 proposals                 │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ verified actions                         │
│  ┌─── 4D Voxel Memory + Action Adapter ──────────────────────────┐  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│ Jetson Orin NX — WBC · CBF · FAST-LIO2 · Tether Safety               │
└──────────────────────────────────────────────────────────────────────┘
```

**What changes:** π0 replaces MPPI as the action generator. V-JEPA 2 becomes a safety checker, not a planner. Cosmos or JEPA for semantic understanding.
**Pros:** π0's flow matching produces extremely smooth trajectories at 50Hz. 3B model fits easily on RTX 5090. Open model.
**Cons:** π0 is manipulation-focused, not locomotion. Needs fine-tuning for whole-body humanoid control. V-JEPA 2 as safety checker adds latency.
**When to use:** Manipulation-heavy tasks. Explore if G1 fine-tuning data is collected.

---

## Variation 7: Minimal Onboard — Distilled

**Philosophy:** Everything distilled to run on the Jetson Orin NX. No tether dependency. Sacrifices model quality for full autonomy.

```
┌──────────────────────────────────────────────────────────────────────┐
│ Jetson Orin NX (Onboard — NO TETHER)                                  │
│                                                                       │
│  ┌─── DISTILLED STUDENT POLICY ──────────────────────────────────┐  │
│  │                                                                │  │
│  │  Teacher: Cosmos 3 Nano (RTX 5090) or GR00T N1                │  │
│  │  Student: Compressed transformer (~200M params, INT8)          │  │
│  │                                                                │  │
│  │  Pipeline:                                                     │  │
│  │  Camera ──→ Frozen ViT Encoder ──→ Tiny Transformer ──→ 43D   │  │
│  │            (pre-computed)          (action head)               │  │
│  │                                                                │  │
│  │  Frequency: 10–20 Hz (limited by Orin NX)                     │  │
│  │  Training: Behavior cloning from teacher on HPC cluster        │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │                                         │
│  ┌─── 4D Voxel Memory (sparse, CUDA) ────────────────────────────┐  │
│  │  Lightweight voxel grid in Orin NX shared memory (4 GB)        │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │                                         │
│  ┌─── WBC + CBF (500 Hz) ────────────────────────────────────────┐  │
│  │  Same reactive safety stack                                    │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  No tether → No link-loss buffer needed. Full autonomy.              │
└──────────────────────────────────────────────────────────────────────┘

  Training (offline, on RTX 5090 or HPC):
  Cosmos 3 Teacher ──→ Behavior Cloning ──→ Distilled Student
  (large, slow)         (paired data)       (small, fast)
```

**What changes:** Everything onboard. No RTX 5090 in the loop. Teacher models only used during training.
**Pros:** Full autonomy — no tether, no network dependency. Can operate anywhere.
**Cons:** Significant quality loss from distillation. 10–20 Hz max. Limited to tasks the student was trained on.
**When to use:** Untethered operation. Field deployment. Backup mode if tether fails.

---

## Variation 8: HPC-Offloaded Training + RTX 5090 Inference

**Philosophy:** Cosmos 3 Super on HPC generates synthetic data and trains policies. Cosmos 3 Nano on RTX 5090 runs inference. Training loop feeds back into deployment.

```
┌──────────────────────────────────────────────────────────────────────┐
│ HPC Cluster (Batch, No Real-Time)                                     │
│                                                                       │
│  ┌─── TRAINING LOOP ─────────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  Cosmos 3 Super (64B)                                          │  │
│  │  ├─ Synthetic Data Generation (SDG)                            │  │
│  │  │  "G1 navigating cluttered lab" → 10,000 video clips         │  │
│  │  │  "G1 picking up tools" → 5,000 action trajectories         │  │
│  │  │  "G1 avoiding pedestrian" → 3,000 edge cases               │  │
│  │  │                                                            │  │
│  │  ├─ Isaac Sim + GR00T-Dreams                                  │  │
│  │  │  Physics-accurate G1 simulation                            │  │
│  │  │  Domain randomization (friction, mass, latency)            │  │
│  │  │                                                            │  │
│  │  └─ Fine-Tuning                                               │  │
│  │     Cosmos 3 Nano post-trained on G1-specific data            │  │
│  │     GR00T N1 fine-tuned on G1 teleoperation                   │  │
│  │     Action adapter MLP trained on paired (29D→43D) data       │  │
│  │                                                                │  │
│  │  Output: Fine-tuned model weights → deployed to RTX 5090      │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                           │ model weights (offline transfer)
┌──────────────────────────▼──────────────────────────────────────────┐
│ RTX 5090 (Offboard) — Cosmos 3 Nano (fine-tuned) + 4D Voxel        │
│ Orin NX (Onboard)  — WBC · CBF · FAST-LIO2                         │
└──────────────────────────────────────────────────────────────────────┘
```

**What changes:** HPC added as training backend. RTX 5090 runs fine-tuned models.
**Pros:** Best model quality (trained on Super, deployed on Nano). Continuous improvement loop.
**Cons:** Requires HPC access and batch job management. Model transfer pipeline needed.
**When to use:** When we have consistent HPC access. Production training workflow.

---

## Variation 9: End-to-End VLA — Simplest Possible

**Philosophy:** Single VLA model directly outputs G1 joint targets. No world model, no planner, no voxel memory. Fastest path to "something working."

```
┌──────────────────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard)                                                   │
│                                                                       │
│  ┌─── END-TO-END VLA ────────────────────────────────────────────┐  │
│  │                                                                │  │
│  │  Camera ──→ [ Vision Encoder ] ──→ [ LLM/VLA ] ──→ 43D Joints │  │
│  │  Text ────→                      (e.g. OpenVLA,               │  │
│  │                                     fine-tuned π0,             │  │
│  │                                     or GR00T N1)               │  │
│  │                                                                │  │
│  │  Frequency: 5–10 Hz                                            │  │
│  │  Training: Open X-Embodiment + G1 teleoperation                │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                       │
│  What's MISSING (by design):                                         │
│  ✗ No world model — no future prediction                             │
│  ✗ No planner — no trajectory optimization                           │
│  ✗ No voxel memory — no object permanence                            │
│  ✗ No safety layer — just raw VLA output                             │
│  ✗ No tether awareness                                               │
│  ✓ Simple, fast to implement, easy to debug                          │
└──────────────────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────────┐
│ Jetson Orin NX                                                       │
│  ┌─── MINIMAL SAFETY ───────────────────────────────────────────┐   │
│  │  WBC: joint limit clamping + basic balance                    │   │
│  │  No CBF, no link-loss buffer, no voxel queries                │   │
│  └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

**What changes:** Everything removed except the VLA and basic WBC.
**Pros:** Simplest possible pipeline. Fastest to implement (~1 week). Easy to debug. Good baseline for comparison.
**Cons:** No safety guarantees. No persistent memory. Blind to rear obstacles. No future prediction. Brittle.
**When to use:** Rapid prototyping. Baseline for A/B testing against more sophisticated architectures.

---

## Variation 10: Cosmos 3 + Isaac GR00T — Full NVIDIA Stack

**Philosophy:** The complete NVIDIA vision for Physical AI. Cosmos, GR00T, Isaac Sim, and NIM microservices working together.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          NVIDIA ECOSYSTEM                             │
│                                                                       │
│  ┌─── DATA GENERATION (HPC) ─────────────────────────────────────┐  │
│  │  Cosmos 3 Super → GR00T-Dreams → Isaac Sim → Synthetic Data    │  │
│  │  (64B, SDG)       (trajectories)    (physics)    (diverse)     │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ training data                            │
│  ┌─── TRAINING (HPC) ────────────────────────────────────────────┐  │
│  │  Isaac Lab · Legged Gym · RL/IL · Domain Randomization         │  │
│  │  → Fine-tuned Cosmos 3 Nano · Fine-tuned GR00T N1              │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                           │ model weights                            │
│  ┌─── INFERENCE (RTX 5090) ──────────────────────────────────────┐  │
│  │                                                                │  │
│  │  ┌──────────────────┐    ┌──────────────────┐                │  │
│  │  │ Cosmos 3 NIM     │    │ GR00T N1 NIM     │                │  │
│  │  │ (Reason+Gen)     │───→│ (System 1+2)     │                │  │
│  │  │ NVFP4 quantized  │    │ TensorRT-LLM     │                │  │
│  │  │ vLLM-Omni serve  │    │ OpenAI-compat API│                │  │
│  │  └──────────────────┘    └────────┬─────────┘                │  │
│  │                                    │ 29D actions               │  │
│  │  ┌─────────────────────────────────▼────────────────────────┐ │  │
│  │  │ Action Adapter (29D→43D) + 4D Voxel Memory               │ │  │
│  │  └──────────────────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                           │ 43D @ 40Hz                               │
│  ┌─── ROBOT (Orin NX) ──────────────────────────────────────────┐  │
│  │  Isaac ROS · WBC · CBF · FAST-LIO2 · TensorRT                │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

**Pros:** Production-grade. NVIDIA-supported end-to-end. NIM for optimized inference. GR00T-Dreams for infinite data.
**Cons:** Heavy NVIDIA lock-in. Requires NGC API keys + NIM licensing. Most complex setup.
**When to use:** Long-term production target. When fully committed to NVIDIA ecosystem.

---

## Comparison Matrix

| Variation | World Model | Action Model | Planner | Onboard Models | Tether Required | Maturity |
|:---|:---|:---|:---|:---|:---|:---|
| **1. Pure JEPA** | V-JEPA 2 | MPPI | MPPI (1024 sample) | WBC + CBF | Yes | ⭐⭐⭐ (papers) |
| **2. Cosmos 3-Centric** | Cosmos 3 | Cosmos 3 (Policy) | None (implicit) | WBC + CBF | Yes | ⭐⭐ (new) |
| **3. GR00T N1-Centric** | GR00T N1 (System 2) | GR00T N1 (System 1) | None (implicit) | WBC + CBF | Yes | ⭐⭐⭐ (mature) |
| **4. Cosmos + GR00T** | Cosmos 3 | GR00T N1 | None | WBC + CBF | Yes | ⭐⭐ (complex) |
| **5. Cosmos + V-JEPA 2** | Cosmos (semantic) + V-JEPA 2 (predictive) | MPPI | MPPI | WBC + CBF | Yes | ⭐⭐ (hybrid) |
| **6. π0 + JEPA** | V-JEPA 2 | π0 (flow match) | JEPA safety check | WBC + CBF | Yes | ⭐⭐ (experimental) |
| **7. Minimal Onboard** | None (implicit) | Distilled student | None | Everything | **No** | ⭐ (limited) |
| **8. HPC-Offloaded** | Cosmos 3 Super → Nano | GR00T N1 | None | WBC + CBF | Yes | ⭐⭐ (training) |
| **9. End-to-End VLA** | None | Single VLA | None | Basic WBC | Yes | ⭐⭐ (simple) |
| **10. Full NVIDIA Stack** | Cosmos 3 | GR00T N1 | None | WBC + CBF | Yes | ⭐ (future) |

---

## Migration Pathways

```
                            ┌──────────────────────┐
                            │  Variation 1          │
                            │  PURE JEPA (Today)    │
                            └──────┬───────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ Variation 5      │  │ Variation 2      │  │ Variation 6      │
    │ Cosmos Semantic  │  │ Cosmos Full      │  │ π0 + JEPA       │
    │ + JEPA Pred.     │  │ (replace both)   │  │ (flow actions)  │
    └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
             │                     │                     │
             │                     ▼                     │
             │           ┌─────────────────┐             │
             └──────────→│ Variation 4      │←────────────┘
                         │ Cosmos + GR00T   │
                         │ (Hybrid)         │
                         └────────┬─────────┘
                                  │
                                  ▼
                        ┌─────────────────────┐
                        │ Variation 10         │
                        │ Full NVIDIA Stack    │
                        │ (Production Target)  │
                        └─────────────────────┘

    Alternative path (autonomy):
    Variation 2 → Variation 8 (HPC training) → Variation 7 (Minimal Onboard)
```

---

## Decision Guide

| If you want... | Start with... |
|:---|:---|
| Something working **today** | Variation 1 (Pure JEPA) |
| **Simplest** path to Cosmos | Variation 2 (Cosmos 3-Centric) |
| **Gradual** migration | Variation 5 (Cosmos Semantic + JEPA Predictive) |
| Best **action quality** | Variation 4 (Cosmos + GR00T Hybrid) |
| **Smooth manipulation** | Variation 6 (π0 + JEPA) |
| **No tether** autonomy | Variation 7 (Minimal Onboard) |
| **Production** deployment | Variation 10 (Full NVIDIA Stack) |
| **Baseline** to beat | Variation 9 (End-to-End VLA) |

---

## Minimum Viable Hardware

**Date:** June 9, 2026
**References:** [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md), [HARDWARE_RISK_REGISTER.md](./HARDWARE_RISK_REGISTER.md), [specs.md](../../../our-project-hardware/specs.md)

**Purpose:** What's the cheapest GPU that can run each variation? Can we go untethered with an upgraded onboard module? This section maps every architecture variation to its minimum viable GPU, covering consumer cards (RTX 30/40/50 series), enterprise cards (RTX 6000 Ada), and edge modules (Jetson AGX Orin, Jetson Thor).

---

### GPU Tier List (June 2026)

| Tier | GPU | VRAM | Architecture | NVFP4? | FP8? | INT8/NF4? | Power | Est. Price | Notes |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **Budget 12GB** | RTX 3060 12GB | 12 GB | Ampere | ❌ | ❌ | ✅ | 170W | ~$250 used | VLA-only, no Cosmos |
| **Budget 16GB** | RTX 4060 Ti 16GB | 16 GB | Ada | ❌ | ✅ | ✅ | 165W | ~$500 | Reasoner-only fits |
| **Budget 16GB** | RTX 4070 Ti Super | 16 GB | Ada | ❌ | ✅ | ✅ | 285W | ~$800 | Best 16GB value |
| **Budget 24GB** | RTX 3090 (used) | 24 GB | Ampere | ❌ | ❌ | ✅ | 350W | ~$700 | Cheapest 24GB — no FP8! |
| **Mid 24GB** | RTX 4090 | 24 GB | Ada | ❌ | ✅ | ✅ | 450W | ~$2,000 | FP8/NF4 for Cosmos |
| **Current 24GB** | RTX 5090 | 24 GB | Blackwell | ✅ | ✅ | ✅ | 575W | ~$2,000 MSRP* | NVFP4 native. We own this. |
| **Enterprise 48GB** | RTX 6000 Ada | 48 GB | Ada | ❌ | ✅ | ✅ | 300W | ~$7,000 | Fits everything simultaneously |
| **Edge 64GB** | Jetson AGX Orin | 64 GB unified | Ampere | ❌ | ❌ | ✅ (INT4) | 15–60W | ~$2,000 module | Untethered, slow, no FP8 |
| **Edge 128GB** | Jetson Thor | 128 GB unified | Blackwell | ✅ | ✅ | ✅ | 40–130W | TBA | Untethered dream — NVFP4 native |

> *\*RTX 5090 MSRP is $1,999 but market prices in June 2026 are ~$5,000+ due to the global GPU supply crisis. We already own ours.*

**Critical architecture notes:**
- **NVFP4 is Blackwell-only.** RTX 40 series (Ada) and RTX 30 series (Ampere) cannot use it. They must fall back to Bitsandbytes NF4 (4-bit), which uses similar VRAM to NVFP4 (~17 GB for Policy, ~8 GB for Reasoner) but runs in software without tensor core acceleration. **FP8 or INT8 Policy mode (~23–25 GB) does NOT fit 24 GB with middleware.**
- **NF4 is the only viable 4-bit option for non-Blackwell GPUs.** Same VRAM footprint as NVFP4, but 2–4× slower inference (no hardware acceleration). Cosmos 3 requires 4-bit quantization on any ≤24 GB GPU.
- **FP8 is Ada+ only.** RTX 3090 (Ampere) lacks FP8 tensor cores — must use NF4 for Cosmos.
- **No consumer GPU >24 GB exists** as of June 2026. The RTX 6000 Ada (48 GB) is the only way to get more VRAM in a single card, at ~$7,000. The RTX 4000 Ada (20 GB) is the cheapest Ada workstation card with >16 GB but is still insufficient for Cosmos Policy + middleware (~20 GB with zero headroom).
- **Jetson AGX Orin is Ampere-based** — no FP8, no NVFP4. Must use INT8 or INT4 for Cosmos. Verified by NVIDIA to run Cosmos series models via JetPack.

---

### Per-Variation Minimum Viable GPU

#### Variation 1: Pure JEPA

| VRAM Required | Standard JEPA: ~12 GB BF16 ✅ | V1 simultaneous: ~33 GB ❌ | V1 sequential: ~22.6 GB INT8 ⚠️ | V1 seq + 10cm vox: ~18.6 GB INT8 ✅ | V1 w/ 2B variant: ~15–17 GB BF16 ✅ |
|:---|:---|:---|:---|:---|:---|

| GPU | VRAM | Verdict | Details |
|:---|:---|:---|:---|
| RTX 3060 12GB | 12 GB | ⚠️ **Standard JEPA only** | V-JEPA 2 + MPPI + Voxel ≈ 10 GB INT8. V1 kitchen sink doesn't fit. 2B variant doesn't fit. |
| RTX 4060 Ti 16GB | 16 GB | ✅ **Standard JEPA comfortable** | ~12 GB BF16 fits with headroom. V1 sequential at INT8 (~22.6 GB) doesn't fit. 2B variant at INT8 (~13–14 GB) fits. |
| RTX 3090 (used) | 24 GB | ✅ **V1 sequential + 2B fits** | INT8 + sequential loops + 10cm voxels = ~18.6 GB. 2B variant (V-JEPA 2.1 ViT-G/16) at BF16 + MPPI + Voxel = ~15–17 GB — fits comfortably. See [VRAM_MEASUREMENTS.md §6](./VRAM_MEASUREMENTS.md#6-corrected-vram-budgets-per-variation). Standard JEPA fits at BF16 with ~12 GB headroom. |
| RTX 4090 | 24 GB | ✅ **V1 sequential + 2B fits** | Same as 3090 but FP8 helps. Standard JEPA and 2B variant both fit easily. |
| RTX 5090 | 24 GB | ✅ **V1 sequential + 2B fits** | NVFP4 doesn't help JEPA but 24 GB is 24 GB. 2B variant (V-JEPA 2.1) is the best quality option. We own this. |
| RTX 6000 Ada | 48 GB | ✅ **V1 simultaneous fits** | All 11 components loaded at once. No model swapping. 2B variant with full kitchen sink also fits. |
| Jetson AGX Orin | 64 GB | ❌ **Too slow** | VRAM sufficient but 275 TOPS inadequate for V-JEPA 2 + MPPI real-time. |

**Cheapest viable (standard JEPA):** RTX 3060 12GB (~$250 used) — remarkably accessible.

**Cheapest viable (V1 kitchen sink):** RTX 3090 (used, ~$700) with INT8 + sequential execution + 10cm voxels.

**V1 with V-JEPA 2.1 2B variant:** RTX 3090 (used, ~$700) — ViT-G/16 (2B) + MPPI + Voxel = ~15–17 GB BF16, fits any 24 GB GPU. Best quality option for our V1 pipeline. See [VRAM_MEASUREMENTS.md §2b](./VRAM_MEASUREMENTS.md#2b-v-jepa-21--dense-feature-upgrade).

**Key insight:** Standard JEPA (what papers run) fits on almost any GPU. Our V1 overloads it with extra perception components, but sequential execution (standard practice) makes it fit on any 24 GB GPU. The "33 GB won't fit" narrative was misleading — it assumed simultaneous loading that no real pipeline does.

---

#### Variation 2: Cosmos 3-Centric

| VRAM Required | NVFP4 Policy: ~20 GB ⚠️ | Reasoner-only: ~11 GB ✅ |
|:---|:---|:---|

| GPU | VRAM | Verdict | Details |
|:---|:---|:---|:---|
| RTX 3060 12GB | 12 GB | ❌ **No** | Policy mode doesn't fit. Reasoner-only at INT8 fits (~10 GB) but no action generation — robot stands still. |
| RTX 4060 Ti 16GB | 16 GB | ⚠️ **Reasoner-only** | Cosmos Policy at NF4 ≈ 17 GB exceeds 16 GB. Reasoner-only (~8 GB NF4 + ~3 GB middleware = ~11 GB) fits comfortably. Robot gets scene understanding but no generated actions — must pair with MPPI fallback planner or reuse last actions. |
| RTX 4070 Ti Super | 16 GB | ⚠️ **Reasoner-only** | Same as above. 16 GB barrier. |
| RTX 3090 (used) | 24 GB | ✅ **Fits** | Policy mode at **NF4** (4-bit) ~17 GB + middleware ~3.2 GB = ~20.2 GB. Fits with ~3.8 GB headroom. ⚠️ Must use NF4 (Bitsandbytes), NOT INT8 — INT8 Policy would be ~25 GB and OOM. NF4 is slower than NVFP4 (software, no tensor core acceleration) but VRAM-identical. |
| RTX 4090 | 24 GB | ✅ **Fits** | Policy mode at **NF4** (4-bit) ~17 GB + middleware = ~20.2 GB. FP8 Policy (~23 GB + middleware = ~26 GB) does NOT fit. NF4 is software-emulated on Ada (no NVFP4 tensor cores), so inference is 2–4× slower than RTX 5090. |
| RTX 5090 | 24 GB | ✅ **Best fit** | NVFP4 native — fastest inference, best power efficiency. We own this. |
| Jetson AGX Orin | 64 GB | 🐌 **Slow but works** | Cosmos verified by NVIDIA on Orin via JetPack. INT4 quantization. Expect 10–30s per Cosmos call (vs 1–10s on RTX 5090). Usable for non-real-time scene queries. Untethered! |
| Jetson Thor | 128 GB | ✅ **Untethered dream** | Blackwell + NVFP4 native + 128 GB. Full RTX 5090-class Cosmos performance, no tether. Not yet released. |

**Cheapest viable for Policy mode:** RTX 3090 (used, ~$700) with NF4 (4-bit) quantization.

**Cheapest viable for Reasoner-only:** RTX 4060 Ti 16GB (~$500). Pair with MPPI fallback planner.

**Untethered minimum:** Jetson AGX Orin 64GB (~$2,000) — slow but autonomous.

---

#### Variation 3: GR00T N1-Centric

| VRAM Required | ~10 GB (GR00T ~7 GB + Voxel ~3 GB) ✅ |
|:---|:---|

| GPU | VRAM | Verdict | Details |
|:---|:---|:---|:---|
| RTX 4060 Ti 16GB | 16 GB | ✅ **Fits** | GR00T + Voxel + Adapter ≈ 10 GB. Comfortable headroom. |
| RTX 3060 12GB | 12 GB | ⚠️ **Tight** | 10 GB in 12 GB — works but minimal headroom for KV cache spikes. |
| RTX 3090 (used) | 24 GB | ✅ **Fits easily** | Overkill for this variation alone. |
| Jetson AGX Orin | 64 GB | ✅ **Untethered viable** | GR00T N1 is designed for edge deployment. INT8 gives ~40 tok/s on 7B models. |

**Cheapest viable:** RTX 3060 12GB (~$250 used) — remarkably accessible.

**Untethered minimum:** Jetson AGX Orin 64GB (~$2,000). GR00T N1 was designed for this.

---

#### Variation 4: Cosmos + GR00T Hybrid

| VRAM Required | Reasoner-only + GR00T: ~18 GB ⚠️ | Full Policy + GR00T: ~27 GB ❌ |
|:---|:---|:---|

| GPU | VRAM | Verdict | Details |
|:---|:---|:---|:---|
| RTX 4060 Ti 16GB | 16 GB | ❌ **No** | Even Reasoner-only (18 GB) exceeds 16 GB. |
| RTX 3090 (used) | 24 GB | ✅ **Reasoner-only fits** | Cosmos Reasoner at NF4 (~8 GB) + GR00T (~7 GB) + middleware (~3 GB) = ~18 GB. Fits with ~6 GB headroom. ⚠️ NF4 only — INT8 Reasoner would be ~12 GB making total ~22 GB (still fits but tight). Full Policy mode needs sequential swap (see Risk Register §4.2). |
| RTX 4090 | 24 GB | ✅ **Reasoner-only fits** | NF4 Reasoner (~8 GB) + GR00T (~7 GB) + middleware (~3 GB) = ~18 GB. Ada's FP8 also works for Reasoner (~12 GB) making total ~22 GB — fits but tighter. NF4 recommended for headroom. |
| RTX 5090 | 24 GB | ✅ **Best fit** | NVFP4 for Cosmos Reasoner. Sequential swap for Policy mode. We own this. |
| RTX 6000 Ada | 48 GB | ✅ **Full Policy + GR00T simultaneously** | The only card that fits both Cosmos Policy (17 GB) + GR00T (7 GB) + middleware (3 GB) = ~27 GB without swapping. |
| Jetson AGX Orin | 64 GB | 🐌 **Reasoner-only, slow** | VRAM sufficient. Both models at INT4 ≈ 22 GB fits. But 275 TOPS makes sequential inference very slow (30–60s per full cycle). |
| Jetson Thor | 128 GB | ✅ **Untethered, full performance** | NVFP4 native. 2,070 TOPS. Both models simultaneously. This is the production untethered target. |

**Cheapest viable:** RTX 3090 (used, ~$700) with NF4 in Reasoner-only mode + sequential swap for Policy.

**Untethered minimum:** Jetson AGX Orin 64GB (~$2,000) — functional but very slow (30–60s cycles).

**Untethered production target:** Jetson Thor (TBA) — full NVFP4 performance, no compromises.

---

#### Variation 5: Cosmos Semantic + JEPA Predictive

| VRAM Required | ~23 GB INT8 (Cosmos Reasoner 8 + JEPA stack 15) ⚠️ |
|:---|:---|

Equivalent to V2 Reasoner-only + V1 Predictive loop. Same constraints as V1 — needs model swapping or reduced resolution to fit 24 GB. See V1 and V2 entries above.

**Cheapest viable:** RTX 3090 (used, ~$700) with INT8 + model swapping.

---

#### Variation 6: π0 VLA + JEPA World Model

| VRAM Required | ~15 GB (π0 3B ≈ 4 GB + V-JEPA 2 INT8 ≈ 5 GB + Voxel ≈ 3 GB + overhead) ✅ |
|:---|:---|

| GPU | VRAM | Verdict |
|:---|:---|:---|
| RTX 4060 Ti 16GB | 16 GB | ✅ **Fits** |
| RTX 3060 12GB | 12 GB | ⚠️ **Tight** |

**Cheapest viable:** RTX 4060 Ti 16GB (~$500).

---

#### Variation 7: Minimal Onboard — Distilled

| VRAM Required | ~4–8 GB (student model ~200M params INT8 ≈ 0.4 GB + Voxel ≈ 3 GB + WBC ≈ 1 GB) ✅ |
|:---|:---|

| GPU | VRAM | Verdict | Details |
|:---|:---|:---|:---|
| Jetson Orin NX (on G1!) | 16 GB | ✅ **Already owned** | 4–8 GB fits easily in 16 GB shared memory. 10–20 Hz inference. No tether. This is the G1's onboard module! |
| Jetson AGX Orin | 64 GB | ✅ **Overkill** | Student model is tiny. No benefit over Orin NX for this variation. |
| RTX 3090 | 24 GB | ✅ **Unnecessary** | V7 is designed for onboard, not offboard. |

**Cheapest viable:** Already owned (Jetson Orin NX 16GB on the G1). This variation was designed for this exact hardware.

**Untethered:** Yes, by definition. No offboard GPU needed.

---

#### Variation 8: HPC-Offloaded Training + RTX 5090 Inference

Training requires HPC (no consumer GPU needed). Inference uses same GPU as V2 or V4. See those sections.

---

#### Variation 9: End-to-End VLA

| VRAM Required | ~6–12 GB depending on VLA size (OpenVLA 7B ≈ 10 GB FP16, π0 3B ≈ 4 GB) ✅ |
|:---|:---|

| GPU | VRAM | Verdict |
|:---|:---|:---|
| RTX 3060 12GB | 12 GB | ✅ **Fits most VLAs** |
| RTX 4060 Ti 16GB | 16 GB | ✅ **Comfortable** |

**Cheapest viable:** RTX 3060 12GB (~$250 used).

---

#### Variation 10: Full NVIDIA Stack

Same as V4 with additional NIM services overhead (~2 GB). Requires same GPUs as V4 plus HPC for training.

**Cheapest viable:** RTX 3090 (used, ~$700) with model swapping + HPC access for training.

---

### Variation 11–14 (LLM/VLM-Enhanced)

From [LLM_AND_VLM_ROLES.md](./LLM_AND_VLM_ROLES.md):

| Variation | Models | VRAM (INT8/NF4) | Min GPU |
|:---|:---|:---|:---|
| **V11: Gemma 4 + MPPI** | Gemma 4 12B (INT8 ≈ 12 GB) + MPPI (2 GB) + Voxel (3 GB) | ~17 GB | RTX 4060 Ti 16GB ❌ — **RTX 3090 24GB** (~$700) |
| **V12: Gemma 4 + Cosmos Reasoner** | Gemma 4 INT8 (12 GB) + Cosmos Reasoner NVFP4 (8 GB) + middleware (3 GB) | ~23 GB ⚠️ | **RTX 3090 24GB** (~$700) — tight |
| **V13: Gemma 4 + Cosmos Policy** | Gemma 4 INT8 (12 GB) + Cosmos Policy NVFP4 (17 GB) + middleware (3 GB) | ~32 GB ❌ | **RTX 6000 Ada 48GB** (~$7,000) only |
| **V14: Gemma 4 (4-bit) + Cosmos Policy + GR00T** | Gemma 4 4-bit (6 GB) + Cosmos Policy (17 GB) + GR00T (7 GB) + mid (3 GB) | ~33 GB ❌ | **RTX 6000 Ada 48GB** (~$7,000) only |

---

### Quick Reference: Cheapest GPU by Variation

| Variation | Mode | Cheapest GPU | Est. Price | Constraints |
|:---|:---|:---|:---|:---|
| **V1** Standard JEPA | Full | RTX 3060 12GB | ~$250 | V-JEPA 2 + MPPI + Voxel = ~10 GB INT8 |
| **V1** Kitchen Sink | Sequential | RTX 3090 (used) | ~$700 | INT8 + sequential loops (standard practice) |
| **V1** 2B (V-JEPA 2.1) | Sequential | RTX 3090 (used) | ~$700 | ViT-G/16 (2B) + MPPI + Voxel = ~15–17 GB BF16 ✅ |
| **V2** Cosmos-Centric | Policy | RTX 3090 (used) | ~$700 | NF4 (4-bit) quantization |
| **V2** Cosmos-Centric | Reasoner-only | RTX 4060 Ti 16GB | ~$500 | No action generation, needs MPPI fallback |
| **V3** GR00T-Centric | Full | RTX 3060 12GB | ~$250 | Remarkably accessible |
| **V4** Cosmos+GR00T | Reasoner-only | RTX 3090 (used) | ~$700 | Sequential swap for Policy mode |
| **V5** Cosmos+JEPA | Swapped | RTX 3090 (used) | ~$700 | INT8 + model swapping |
| **V6** π0+JEPA | Full | RTX 4060 Ti 16GB | ~$500 | — |
| **V7** Minimal Onboard | Full | Jetson Orin NX 16GB | Owned | Already on the G1! |
| **V9** End-to-End VLA | Full | RTX 3060 12GB | ~$250 | No safety, no memory |
| **V11** Gemma 4 + MPPI | Full | RTX 3090 (used) | ~$700 | — |
| **V12** Gemma 4 + Cosmos | Reasoner | RTX 3090 (used) | ~$700 | Tight (23/24 GB) |
| **V13** Gemma 4 + Cosmos | Policy | RTX 6000 Ada 48GB | ~$7,000 | Only enterprise fits |

---

### Untethered Viability Analysis

**Can we remove the tether and run everything on the robot?**

| Onboard Module | VRAM | Architecture | Cosmos Viable? | Real-Time? | Battery Viable? |
|:---|:---|:---|:---|:---|:---|
| **Jetson Orin NX** (on G1) | 16 GB shared | Ampere | ❌ No — too small, too slow | ❌ | ✅ 15W |
| **Jetson AGX Orin 64GB** | 64 GB unified | Ampere | 🐌 Yes, INT4, very slow | ❌ 30–60s per Cosmos cycle | ⚠️ 30–60W |
| **Jetson Thor** | 128 GB unified | Blackwell | ✅ NVFP4 native, full speed | ✅ 128 GB fits all models | ⚠️ 40–130W |

#### Jetson AGX Orin 64GB — Detailed Analysis

- **Architecture:** Ampere — NO FP8, NO NVFP4. Must use INT8 or INT4.
- **Unified memory:** ~50–55 GB usable after OS. Enough for Cosmos + GR00T at INT4 (~22 GB).
- **TOPS:** 275 SPARSE INT8 vs RTX 5090's massive throughput (Blackwell tensor cores). **10–50× slower for transformer inference.**
- **Cosmos 3:** NVIDIA verified that Cosmos models run on Orin via JetPack. Realistic inference time: 15–60 seconds per full Cosmos call.
- **GR00T N1:** Designed for edge deployment. ~10–40 tok/s at INT4 on 7B-class models. Reasonable for real-time action generation alone.
- **Power:** 30–40W is realistic for sustained inference. The G1's battery must supply this in addition to 43 motors.
- **Verdict:** Technically capable of running V2 (Cosmos Reasoner-only) or V4 (Cosmos Reasoner + GR00T) untethered. But **cycle times are measured in tens of seconds, not milliseconds.** Suitable for deliberate task planning and non-real-time scene understanding. Not suitable for 40 Hz reactive control.

#### Jetson Thor — The Untethered Upgrade Path

- **Architecture:** Blackwell — NVFP4 native! Full Cosmos 3 performance.
- **Unified memory:** 128 GB LPDDR5X. Can fit Cosmos Policy + GR00T N1 + Gemma 4 + Voxel + WBC simultaneously.
- **TOPS:** ~2,070 FP4. Comparable to desktop RTX 5090-class throughput.
- **Power:** 40–130W. Higher than Orin but still battery-viable for a humanoid.
- **Status:** Announced but not yet released as of June 2026.
- **Verdict:** This is the hardware that makes full untethered Cosmos + GR00T viable. When available, it obsoletes the tether for V2, V3, V4, V10, and V12.

---

### Hardware Upgrade Paths

```
                          ┌─────────────────────────┐
                          │ WE OWN: RTX 5090 (24GB)  │
                          │ + Jetson Orin NX (16GB)  │
                          │ + HPC (batch)            │
                          └───────────┬──────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ BUDGET UPGRADE   │       │ UNTETHERED NOW   │       │ ENTERPRISE PATH   │
│                  │       │                  │       │                  │
│ RTX 3090 (used)  │       │ Jetson AGX Orin  │       │ RTX 6000 Ada     │
│ ~$700            │       │ 64GB ~$2,000     │       │ 48GB ~$7,000     │
│                  │       │                  │       │                  │
│ • Second GPU for │       │ • Swap into G1   │       │ • Fits V1 without│
│   dedicated      │       │ • No tether!     │       │   model swapping │
│   inference      │       │ • Slow but       │       │ • Fits V13 full   │
│ • V2/V4 viable   │       │   autonomous     │       │ • No compromises  │
│ • Cheapest 24GB  │       │ • GR00T runs well│       │ • Workstation PCIe│
└──────────────────┘       └──────────────────┘       └──────────────────┘
          │                           │                           │
          ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ UNTETHERED       │       │ FUTURE PROOF     │       │                  │
│ FUTURE           │       │                  │       │                  │
│ Jetson Thor      │       │ Jetson Thor      │       │                  │
│ 128GB (TBA)      │       │ 128GB (TBA)      │       │                  │
│ Blackwell + NVFP4│       │ Full performance │       │                  │
└──────────────────┘       └──────────────────┘       └──────────────────┘
```

**Recommended path for our project:**
1. **Now:** RTX 5090 (owned) → V2 (Cosmos-Centric) or V4 (Cosmos+GR00T Reasoner-only)
2. **Budget expansion:** Add RTX 3090 as dedicated inference GPU (~$700) → run V4 Policy mode on 5090, Reasoner on 3090 simultaneously
3. **Untethered experiment:** Jetson AGX Orin 64GB (~$2,000) → V7 (Distilled) or V3 (GR00T-only) for autonomous operation
4. **Untethered production:** Jetson Thor when available → V4 or V10 untethered at full NVFP4 performance
5. **No-compromises:** RTX 6000 Ada 48GB (~$7,000) → V1 without swapping, V13 full, everything simultaneously

---

### Key Takeaways

1. **RTX 5090 (24 GB, owned) is sufficient for V2, V3, V4 Reasoner-only.** It's tight but workable. We don't need to buy anything to start.

2. **16 GB is the Cosmos Policy barrier.** Cosmos Policy mode at any 4-bit quantization is ~17 GB — just over the 16 GB line. 16 GB GPUs can only run Reasoner-only mode. This is a critical threshold.

3. **Standard JEPA fits on almost any GPU.** V-JEPA 2 + MPPI + Voxel = ~12 GB BF16 → RTX 3060 12GB (~$250). V-JEPA 2.1 ViT-G/16 (2B) + MPPI + Voxel = ~15–17 GB BF16 → fits any 24 GB GPU comfortably. Our V1 adds extra perception components; with sequential execution it fits any 24 GB GPU at INT8 (or at BF16 with the 2B variant).

4. **No consumer GPU fits V1 or V13 if loaded simultaneously.** But with sequential execution (standard practice), V1 fits any 24 GB GPU at INT8. Full V13 (Gemma 4 + Cosmos Policy) at 32 GB requires RTX 6000 Ada or model swapping.

5. **NVFP4 is Blackwell-only. NF4 is the non-Blackwell equivalent for VRAM.** RTX 4090/3090 must use Bitsandbytes NF4 (4-bit) for Cosmos Policy to fit — NOT INT8 or FP8, which would exceed 24 GB. NF4 matches NVFP4's VRAM footprint (~17 GB Policy) but runs 2–4× slower without hardware tensor core acceleration. See [VRAM_MEASUREMENTS.md §4](./VRAM_MEASUREMENTS.md#4-cosmos-3-nano--nvfp4-quantized) for the precision breakdown.

6. **Jetson AGX Orin makes untethered Cosmos possible, but slow.** 15–60 second cycle times. Viable for deliberation, not for reactive control. Pair with V7 (distilled student) for real-time loops.

7. **Jetson Thor is the real untethered answer.** Blackwell + NVFP4 + 128 GB + 2,070 TOPS. When it ships, the tether becomes optional for all variations.

8. **V7 (Minimal Onboard) already works untethered on our existing Orin NX.** The distilled student approach gives us autonomous operation today, even if quality is reduced.
