# Literature-Backed Architecture Improvements

*Cross-referencing the G1-JEPA-World-Model brainstorm against the 42 papers in the wiki vault.*

---

## 1. World Model: Replace V-JEPA 2 + MPPI with a modular, compute-realistic stack

### Current design
V-JEPA 2 (ViT-g, ~1B params) inside MPPI (1024 samples × 15 steps @ 40Hz) — ~100-1000× beyond realistic compute.

### Recommended replacement

**Encoder: LeJEPA (2511.08544v3)** instead of V-JEPA 2
- No teacher-student, no stop-gradients, single hyperparameter λ
- ViT-L (304M, 3× smaller than ViT-g) outperforms I-JEPA ViT-H (632M)
- Training loss correlates 94.5% with downstream accuracy — model selection without downstream evaluation
- Architecture-agnostic (ConvNets, ViTs, ResNets all work) → can target edge deployment
- In-domain pretraining on small datasets outperforms transfer from frontier models

**Planner: Active Neural SLAM modular decomposition (2004.05155v1)** instead of latent MPPI
- ANS showed modularity enables zero-shot task transfer (exploration → PointGoal: 95% vs 82.7%)
- Replace the monolithic MPPI with: voxel memory → VLA goal selector → analytical path planner → local controller
- Use A* or RRT* through the voxel grid instead of 1024-sample latent-space search
- This decouples the planning frequency problem: the voxel grid updates at 5-10Hz, the planner runs near-instantly

**Noise robustness: EchoJEPA insight (2602.02603v4)**
- JEPA representations are 86% more robust to domain-specific noise than pixel reconstruction
- Apply the multi-view probing framework to fuse RGB + depth + proprioception into a unified representation

**Action-space learning: Genie-inspired (2402.15391v1)**
- The latent action discovery concept is valuable, but don't use the 11B-parameter Genie directly
- Instead, learn a small discrete latent action space (8-64 actions) from G1 egocentric video
- Combine with I-JEPA's finding that predicting in representation space (not pixel space) is critical

---

## 2. Perception: DINOv3 alone can replace Slot Attention

### Current design
DINOv3 for segmentation + Slot Attention for object binding.

### Recommended change

**Drop Slot Attention, use DINOv3 patch features directly**
- Slot Attention (2006.15055v2) was only validated on synthetic datasets (CLEVR, Tetrominoes)
- The paper itself acknowledges: "Slot Attention does not inherently know about objects — segmentation is driven solely by the downstream task"
- DINO (2104.14294v2) already exhibits emergent semantic segmentation in self-attention maps (45.9% Jaccard vs 22.0% supervised)
- DINOv3 (2508.10104v1) scales this to 7B parameters with Gram anchoring for dense feature quality
- The distilled ViT-L variant eliminates the need for a separate object-binding module

**If object tracking is still needed:** Use DINOv3 features with a lightweight clustering head (k-means on patch features), which is simpler and more robust than iterative Slot Attention.

**Pretraining on robot data:** Use LeJEPA instead of DINOv3 if you need to pretrain a domain-specific encoder on G1 egocentric data. LeJEPA's training-loss-as-proxy property (94.5% Spearman correlation) means you can select the best checkpoint without running expensive downstream evaluations.

---

## 3. Control Stack: Replace custom WBC/CBF with G1-validated controllers

### Current design
FAST-LIO2 + WBC + CBF @ 500Hz on Orin NX, designed from scratch.

### Recommended replacement

The vault contains **six G1-validated control papers** that are directly deployable:

| Paper | What it provides | Where it fits |
|---|---|---|
| **ULTRA** (2603.03279v1) | Physics-driven retargeting → distillation → RL fine-tuning pipeline. Real G1: 73% tracking, 80-90% goal following | **Primary control architecture** — most complete template |
| **HUGWBC** (2502.03206v2) | Intervention training decouples upper-body from lower-body control. Noise curriculum for robustness | **Locomotion layer** beneath a VLA policy |
| **HOST** (2502.08378v2) | Multi-critic RL for standing-up on G1. Emergent fall recovery. Outdoors-tested | **Fall recovery primitive** in the safety stack |
| **FIRM** (2511.07407v1) | Unified fall prevention + impact mitigation + recovery. 10/10 flat, 8/10 slippery on G1 | **Safety layer** — directly deployable |
| **Gait-conditioned RL** (2505.20619v3) | Single recurrent policy for standing/walking/running/transitions on G1 | **Multi-gait locomotion** without policy switching |
| **ASAP** (msr-thesis) | Delta action model for sim-to-real gap. Ankle joints show largest discrepancy on G1 | **Sim-to-real correction** layer |

**Recommended integration:**
1. Use ULTRA's four-stage pipeline as the primary control architecture
2. Layer HUGWBC's intervention training for upper/lower body decoupling
3. Add FIRM as the fall-safety layer (replaces HJI reachability — see below)
4. Apply ASAP's delta action model for sim-to-real correction
5. Retain the TrajectoryBuffer link-loss safety from the original design

---

## 4. Safety: Replace HJI Reachability with deployable alternatives

### Current design
Hamilton-Jacobi reachability analysis in learned latent space — an open research problem.

### Recommended replacement

**Primary: FIRM fall-safety policy (2511.07407v1)**
- Already deployed and validated on Unitree G1
- 10/10 success on flat mat, 8/10 on slippery surfaces
- Unified fall prevention + impact mitigation + recovery in a single diffusion policy
- Trained from only 5 human demonstrations

**Secondary: Uncertainty-triggered damping (already in the original design)**
- When voxel memory age exceeds threshold → trigger conservative behavior
- This is implementable today and addresses the same concern as HJI (out-of-distribution safety)

**Tertiary: EchoJEPA noise robustness (2602.02603v4)**
- JEPA representations are 86% more robust to noise than pixel reconstruction
- Apply this principle to make the safety layer robust to sensor degradation

---

## 5. VLA Integration: Fine-tune an existing VLA instead of building from scratch

### Current design
Custom VL-JEPA + MPPI + 4D-NVS + Slot Attention — a multi-component custom stack.

### Recommended simplification

**GR00T + modality augmentation (2512.01358v1)** is the most directly applicable recipe:
- GR00T N1.5 (3B params) fine-tuned on G1 with contact-force signals
- Achieves 94% success on G1 Pick Apple to Bowl (vs 0% zero-shot, 48% standard fine-tuning)
- Shows that modality design (contact forces, depth) is the key lever, not model scale
- Single A6000 GPU, 20k fine-tuning steps

**RT-2 (2307.15818v1)** validates the VLA paradigm:
- Co-fine-tuning VLMs on web data + robot trajectories transfers semantic knowledge to actions
- 62% success on unseen objects vs 29% for robot-data-only baseline
- Chain-of-thought reasoning emerges (e.g., "pick up the object that can be used to write" → pen)

**PaliGemma (2407.07726v2)** is the open-source VLM backbone:
- Sub-3B (400M SigLIP + 2B Gemma) matches 55B PaLI-X and 562B PaLM-E
- Simple linear connector outperforms MLP connector
- 256 fine-tuning examples reach within 20% of full-data performance
- Open model weights and training code

**Recommended VLA path:**
1. Start with PaliGemma or GR00T as the foundation VLA
2. Fine-tune on G1 data with modality augmentation (depth + contact forces)
3. Use the fine-tuned VLA for both semantic goal selection and action generation
4. This replaces the custom VL-JEPA + MPPI + EBC pipeline with a single model

---

## 6. Dynamic Scene Memory: Replace 4D-NVS with a temporal voxel grid

### Current design
4D Neural Voxel Splatting (HexPlane-based dynamic scene rendering) consuming 4GB VRAM.

### Recommended replacement

**Simple temporal voxel grid with feature decay** instead of 4D-NVS
- 4D-NVS (2511.00560v2) was designed for novel-view synthesis, not real-time robotics
- The paper itself notes: "Deployment on actual edge hardware is discussed motivationally but not empirically demonstrated"
- What the planner actually needs: occupancy + semantic class + observation age for each voxel
- A hash-based sparse voxel grid (MinkowskiNet features + timestamps) provides this at a fraction of the VRAM cost
- Saves ~3.5GB VRAM that can be reallocated to the VLA or world model

**VoxFormer (from the original design)** remains the right template for the spatial memory structure — keep it.

---

## 7. Training Improvements: LeJEPA + SimCLR augmentation principles

### Pretraining encoder on robot data
LeJEPA (2511.08544v3):
- Heuristics-free: no stop-gradients, no teacher-student, no EMA, single hyperparameter λ
- Stable training on ViT-gigantic (1.8B params) with no collapse
- In-domain pretraining on small datasets (Galaxy10, Food101) substantially outperforms DINOv2/DINOv3 transfer

### Data augmentation
SimCLR (2002.05709v3):
- Composition of multiple augmentations (crop + color distortion + blur) is critical
- Self-supervised learning benefits more from stronger augmentation than supervised learning
- Apply aggressive augmentation to robot egocentric data during pretraining

### Training loss as model selector
LeJEPA's 94.5% Spearman correlation between training loss and downstream accuracy means you can select the best pretrained checkpoint without running expensive robot evaluations.

---

## 8. Architecture Template: Active Neural SLAM modular decomposition

The single most important architectural insight from the literature:

ANS (2004.05155v1) showed that a modular decomposition (SLAM → global policy → analytical planner → local policy) achieves 94.8% coverage vs 78.9% for end-to-end RL, and transfers zero-shot to new tasks.

**Apply this to the G1-JEPA architecture:**

| ANS Component | G1-JEPA Equivalent | Backed by |
|---|---|---|
| Neural SLAM (map builder) | Sparse Voxel Latent Memory (MinkowskiNet + VoxFormer) | Original design |
| Global policy (goal selector) | Fine-tuned VLA (GR00T / PaliGemma) | 2512.01358v1, 2307.15818v1 |
| Analytical planner | A* / RRT* through voxel grid | 2004.05155v1 |
| Local policy (controller) | ULTRA / HUGWBC whole-body controller | 2603.03279v1, 2502.03206v2 |
| Safety fallback | FIRM + CBF + TrajectoryBuffer | 2511.07407v1 |

---

## Summary of Recommended Changes

| Component | Remove | Replace with | Why |
|---|---|---|---|
| World model | V-JEPA 2 (ViT-g) | LeJEPA (ViT-L, 304M) | 3× smaller, better transfer, heuristics-free |
| Planner | MPPI 1024 samples @ 40Hz | A* through voxel grid + VLA goal selector | 1000× fewer compute, ANS-validated modularity |
| Perception | Slot Attention | DINOv3 patch features + clustering | Only validated on synthetic data; DINO already segments |
| Dynamic memory | 4D-NVS (4GB VRAM) | Temporal voxel grid with feature decay | Saves 3.5GB VRAM, wrong tool for the job |
| Safety | HJI reachability | FIRM fall-safety + uncertainty damping | FIRM already deployed on G1 (10/10 success) |
| Control | Custom WBC/CBF | ULTRA pipeline + HUGWBC intervention | 6 G1-validated papers available |
| High-level | Custom VL-JEPA | Fine-tuned VLA (GR00T / PaliGemma) | 94% success on G1, simpler architecture |
| Training | DINO/DINOv2 pretraining | LeJEPA for domain-specific data | Better small-data transfer, training-loss-as-proxy |

The resulting architecture is simpler, more modular, literature-validated, and realistically deployable on available hardware.
