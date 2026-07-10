# Cosmos 3, GR00T, VLAs & Our G1 Architecture: Research Synthesis

**Date:** June 9, 2026
**Context:** Brainstorming how the Unitree G1 humanoid interacts with its environment given our hardware (Orin NX onboard + RTX 5090 offboard + HPC cluster).

---

## 1. Recap: Our Current G1-JEPA Architecture

We've designed a **tethered, non-SLAM, hierarchical world model** architecture with three control loops:

| Loop | Frequency | Hardware | Key Components |
|:---|:---|:---|:---|
| **Semantic** | 0.5–1 Hz | RTX 5090 | DINOv3 + Slot Attention + 3DGS + VL-JEPA |
| **4D Predictive** | 5–40 Hz | RTX 5090 | V-JEPA 2 + MinkowskiNet + 4D-NVS + MPPI |
| **Reactive** | 500 Hz | Orin NX | FAST-LIO2 + CBF + Link-Loss Buffer |

**Core Innovation:** 4D Sparse Voxel Latent Memory provides object permanence for the G1's blind spots (especially rearward navigation where the Livox MID-360's 59° vertical FOV creates a heel-level blind zone). Instead of traditional SLAM costmaps, we use energy-based constraints in latent space to define "no-go" zones.

---

## 2. NVIDIA Cosmos 3 — The Game Changer

### What It Is
Cosmos 3 (released May 31, 2026) is an **omnimodal world foundation model** that treats language, images, video, audio, and **physical actions** as native modalities. This is fundamentally different from previous models that were vision-only or text-only.

### Architecture: Mixture-of-Transformers (MoT)
- **Reasoner Tower:** An autoregressive VLM that interprets multimodal inputs and understands physical context (motion, object interaction, causality).
- **Generator Tower:** A diffusion-based model that produces future video observations and action sequences, conditioned on the Reasoner's understanding.

This two-tower design means Cosmos 3 can both *understand* a scene and *generate* physically plausible futures — it's both a world model AND an action model.

### Model Sizes & Hardware Fit
| Variant | Size | Hardware | Relevance to Us |
|:---|:---|:---|:---|
| **Cosmos 3 Nano** | 16B (8B Reasoner + 8B Generator) | RTX 5090 ✅ | **Directly runnable on our offboard laptop** |
| **Cosmos 3 Super** | 64B | H100/B200 datacenter | Usable on our HPC cluster for training |

With NVFP4 quantization, inference can be up to 2× faster, making the Nano variant very practical on a 24GB RTX 5090.

### What This Means for Our Project

**1. Cosmos 3 could replace or absorb multiple components of our Semantic + Predictive loops:**
- **DINOv3 + Slot Attention → Cosmos 3 Reasoner:** The Reasoner tower already performs visual scene understanding, object segmentation, and semantic grounding — no need for separate DINO + Slot Attention pipelines.
- **V-JEPA 2 → Cosmos 3 Generator:** The Generator tower produces action-conditioned future predictions natively. V-JEPA 2's latent prediction becomes a subset of what Cosmos 3 does.
- **VL-JEPA → Cosmos 3 Reasoner:** Language grounding is built-in; the Reasoner processes natural language commands and grounds them in the physical scene.

**2. Synthetic data generation (SDG) becomes trivial:**
- Cosmos 3 can generate infinite physically-plausible training scenarios from prompts
- Combine with our 3DGS captures of the actual lab for "digital twin" training
- This directly addresses the sim-to-real gap by generating diverse training data

**3. Action as a native modality:**
- Unlike V-JEPA 2 which requires separate action-conditioning fine-tuning, Cosmos 3 treats actions as a first-class modality
- This means we can query: "Given this scene, what actions lead to the goal state?" and get both the predicted video AND the action trajectory

**4. The non-SLAM approach is validated:**
- Cosmos 3 is fundamentally a world model, not a geometric mapper — it aligns perfectly with our mapless JEPA philosophy
- It learns physics and causality from data rather than explicit geometric models

### Limitations
- **Latency:** Even the 16B Nano model, fully quantized, probably won't run at 40Hz inference. Our hierarchical split (Cosmos 3 at 0.5–5 Hz for high-level planning, with a distilled student for the 40Hz loop) remains necessary.
- **Not a drop-in replacement for the voxel memory:** Cosmos 3 has context windows, not persistent spatial memory. Our 4D Voxel Latent Memory remains critical for object permanence during rearward navigation.

---

## 3. NVIDIA GR00T — The Embodiment Layer

### What It Is
GR00T is not a single model but a **multi-layered platform** for embodied AI:

| Component | Role |
|:---|:---|
| **GR00T N1/N1.x** | VLA foundation model — the "brain" that outputs motor actions |
| **Isaac GR00T** | Development platform for sim, training, and deployment |
| **GR00T-Dreams** | Synthetic data pipeline powered by Cosmos world models |
| **Reference Humanoid Design** | Open-source hardware blueprint (Unitree G1 compatible) |

### GR00T N1 Architecture
Uses a **dual-system design** inspired by human cognition:
- **System 1 (Fast):** Low-latency reflexive motor control
- **System 2 (Slow):** Deliberative reasoning, planning, task decomposition

This maps elegantly to our three-loop hierarchy — System 2 is our Semantic loop, System 1 maps to our Predictive + Reactive loops.

### Unitree G1 Support
The G1 is explicitly supported in the GR00T ecosystem. NVIDIA provides:
- Isaac Sim models for the G1
- Teleoperation data collection pipelines
- Deployment tooling (TensorRT, ROS 2 integration)

### Cosmos 3 + GR00T Integration
These are **complementary**, not competing:
- **Cosmos 3** = the world understanding & prediction engine
- **GR00T N1** = the specialized robot action model
- Pipeline: Cosmos 3 understands the scene → GR00T N1 translates to motor commands

### What This Means for Our Project
- **GR00T N1 could serve as our action generation layer**, replacing the custom MPPI planner with a learned VLA policy
- **Isaac GR00T + Isaac Sim** gives us a mature simulation pipeline, replacing custom Isaac Gym/Gazebo setups
- **GR00T-Dreams** leverages Cosmos for synthetic data — we get this for free if we adopt both

---

## 4. PI Zero (π0) & The VLA Landscape

### The Shift from Tokenized to Continuous Actions
The field has decisively moved away from discrete action tokenization (RT-2, OpenVLA) toward **flow matching / diffusion-based continuous action models**. This matters enormously for humanoids because:
- Discrete tokenization causes jerky motions that can damage actuators
- Continuous flow models produce smooth, physically-plausible trajectories at 50Hz

### PI Zero (π0) Architecture
- **Base:** 3B parameter pre-trained VLM (PaliGemma or similar)
- **Action Head:** Flow matching (diffusion variant) outputs continuous action chunks at 50Hz
- **Training Data:** Open X-Embodiment + proprietary data from 8 robot platforms
- **Hardware:** RTX 5090 can easily run the 3B model at 50Hz

### Key Limitation: Manipulation, Not Locomotion
π0's primary demonstrated capability is **dexterous manipulation** (folding laundry, packing groceries, assembling boxes). It controls arms and hands, not legs. Whole-body humanoid locomotion — coordinating 43 DoF with balance constraints — is fundamentally different from 7-DoF arm control.

That said, the flow matching approach is applicable to whole-body control. The question is whether anyone has trained a π0-style model on humanoid locomotion data at scale.

### Other VLAs Worth Watching

| Model | Architecture | Action Space | Best For |
|:---|:---|:---|:---|
| **π0** | Flow matching on 3B VLM | Continuous, 50Hz | Dexterous manipulation |
| **GR00T N1** | Dual-system VLA | Continuous w/ System 1/2 split | General humanoid skills |
| **OpenVLA** | 7B LLM + vision encoder | Tokenized (discrete bins) | Research, easy fine-tuning |
| **RT-2** | PaLM-E / PaLI-X backbone | Tokenized | General household tasks |
| **NanoVLA** | Distilled, compressed VLA | Continuous | Edge deployment (Orin-level) |

### The Edge Deployment Problem
**You cannot run a 7B+ VLA on the Jetson Orin NX at control frequency.** Best practices:
1. **Distillation:** Train a small "student" policy (MLP or tiny transformer) that mimics the large VLA's output; run the student on the Orin NX
2. **Split execution:** Large VLA on RTX 5090 outputs goals at 1–5 Hz; low-level WBC on Orin NX interpolates at 500 Hz
3. **NanoVLA approach:** Compress the vision encoder (freeze + prune), quantize to INT8, accept some accuracy loss for speed

Our tethered architecture already implements strategy #2, which is the most robust approach.

---

## 5. Synthesis: How These Fit Together

### Architecture Option A: Cosmos 3-Centric
```
┌─────────────────────────────────────────────────────────┐
│ RTX 5090 (Offboard, Gigabit Ethernet)                    │
│                                                          │
│  ┌──────────────────────────────────────┐               │
│  │ Cosmos 3 Nano (16B, NVFP4)           │               │
│  │  • Scene understanding (Reasoner)    │  0.5–5 Hz     │
│  │  • Future prediction (Generator)     │               │
│  │  • Language grounding                │               │
│  │  • Action trajectory proposals       │               │
│  └──────────────┬───────────────────────┘               │
│                 │ latent goals + action chunks          │
│  ┌──────────────▼───────────────────────┐               │
│  │ 4D Voxel Latent Memory              │               │
│  │  • Object permanence                │  10–40 Hz     │
│  │  • Rearward blind spot queries      │               │
│  │  • Uncertainty-triggered damping    │               │
│  └──────────────┬───────────────────────┘               │
│                 │ refined trajectories                  │
│  ┌──────────────▼───────────────────────┐               │
│  │ MPPI Planner (1024 trajectories)    │  40 Hz         │
│  │  • Tether yaw penalty               │               │
│  │  • Energy-based constraints         │               │
│  └──────────────┬───────────────────────┘               │
└─────────────────┼───────────────────────────────────────┘
                  │ joint targets @ 40Hz
┌─────────────────▼───────────────────────────────────────┐
│ Jetson Orin NX (Onboard)                                │
│                                                          │
│  ┌──────────────────────────────────────┐               │
│  │ Whole-Body Controller (WBC)          │  500 Hz        │
│  │  • Inverse kinematics/dynamics       │               │
│  │  • CBF safety filter                 │               │
│  │  • Link-loss trajectory buffer       │               │
│  └──────────────┬───────────────────────┘               │
│                 │ motor commands                        │
│  ┌──────────────▼───────────────────────┐               │
│  │ FAST-LIO2 Odometry + IMU            │  200 Hz        │
│  └──────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

### Architecture Option B: GR00T N1-Centric
Same structure, but replace Cosmos 3 + MPPI with GR00T N1 as the action generation layer:
- **GR00T N1 System 2** (slow reasoning) replaces our Semantic loop
- **GR00T N1 System 1** (fast control) outputs at 40Hz to the Orin NX
- Voxel memory still sits between GR00T and the WBC for spatial persistence

### Architecture Option C: Hybrid (Cosmos 3 + GR00T N1)
- Cosmos 3 handles world understanding, scene prediction, and goal generation
- GR00T N1 translates Cosmos 3 outputs into motor-level action trajectories
- This leverages NVIDIA's intended complementary design

### Which Option?
| Criterion | Option A (Cosmos 3) | Option B (GR00T N1) | Option C (Hybrid) |
|:---|:---|:---|:---|
| **Simplicity** | ⭐⭐⭐ Fewest components | ⭐⭐ Two models | ⭐ Most complex |
| **World understanding** | ⭐⭐⭐ Native omnimodal | ⭐⭐ VLA-focused | ⭐⭐⭐ Best of both |
| **Action quality** | ⭐⭐ Generator outputs proposals | ⭐⭐⭐ Purpose-built VLA | ⭐⭐⭐ GR00T for actions |
| **Hardware fit** | ⭐⭐ 16B model on 5090 | ⭐⭐⭐ Lighter policies | ⭐⭐ Both models needed |
| **Ecosystem** | ⭐⭐ New (May 2026) | ⭐⭐⭐ Mature Isaac stack | ⭐⭐⭐ Full NVIDIA stack |
| **Research alignment** | ⭐⭐⭐ Novel, cutting-edge | ⭐⭐ Standard approach | ⭐⭐ Less focused |

### Strategic Recommendation

**Phase 1 (Now):** Stick with our current V-JEPA 2 + MPPI approach. It's well-understood, we have the paper implementations, and it directly addresses our unique tethered + voxel memory constraints. The research is solid.

**Phase 2 (Explore):** Experiment with Cosmos 3 Nano on the RTX 5090 as a *replacement* for the Semantic loop (DINO + Slot Attention + VL-JEPA). Compare quality of scene understanding and goal generation vs. our current stack.

**Phase 3 (Future):** If Cosmos 3 proves effective, adopt the full NVIDIA stack (Cosmos 3 + GR00T N1 + Isaac GR00T) for maximum ecosystem leverage. This would give us:
- Cosmos 3 for world modeling and synthetic data
- GR00T N1 for action generation
- Isaac Sim for physics simulation
- GR00T-Dreams for automated data generation

---

## 6. Key Insights & Implications

### What's Validated
1. **The tethered architecture is correct.** Cosmos 3 Nano (16B) needs the RTX 5090. The Orin NX can't run these models. Our split is architecturally sound.
2. **The non-SLAM approach is the future.** Cosmos 3, V-JEPA 2, and GR00T are all world-model-based, not geometry-based. We were right to move away from SLAM.
3. **The 4D Voxel Memory is our unique contribution.** No other system (Cosmos, GR00T, π0) has explicit persistent spatial memory for blind spots. This is our differentiator.
4. **Hierarchical control is standard.** The three-loop split (semantic → predictive → reactive) is exactly what the field is converging on.

### What's Challenged
1. **DINO + Slot Attention may be redundant.** Cosmos 3's Reasoner tower handles object-centric scene understanding natively. We might drop these components.
2. **V-JEPA 2 may be superseded.** Cosmos 3's Generator tower does what V-JEPA 2 does, but with action as a native modality and better physics grounding.
3. **Our MPPI planner may become unnecessary.** If GR00T N1 or a fine-tuned Cosmos 3 can output action trajectories directly, the sampling-based MPPI becomes an optimization detail rather than a core component.

### What Stays Unique to Us
1. **Tether-aware planning** (yaw penalty, cable management) — no existing system models this
2. **Acoustic-JEPA** (audio hazard cones in voxel memory) — unique multimodal safety feature
3. **Link-loss trajectory buffer** — our specific hardware constraint solution
4. **G1-specific kinematics** — whole-body control tuned for the G1's 43 DoF

---

## 7. Action Items

### Immediate (This Week)
- [ ] Download and benchmark Cosmos 3 Nano on the RTX 5090
- [ ] Test inference latency at different quantization levels (BF16 → FP8 → NVFP4)
- [ ] Evaluate scene understanding quality vs. our DINO + Slot Attention pipeline

### Short-Term (Next 2 Weeks)
- [ ] Prototype Cosmos 3 as Semantic loop replacement
- [ ] Evaluate GR00T N1 for action generation
- [ ] Compare Cosmos 3 action proposals against our MPPI planner

### Medium-Term (Next Month)
- [ ] If Cosmos 3 is viable, design full migration plan to NVIDIA ecosystem
- [ ] Integrate with Isaac Sim for physics-accurate G1 simulation
- [ ] Explore GR00T-Dreams for automated training data generation

### Keep Regardless
- [ ] 4D Voxel Latent Memory (our key differentiator)
- [ ] Tether safety and link-loss buffer
- [ ] CBF-based reactive safety layer
- [ ] Acoustic-JEPA hazard detection

---

## References

- [NVIDIA Cosmos 3 Announcement](https://nvidianews.nvidia.com/news/nvidia-launches-cosmos-3-the-open-frontier-foundation-model-for-physical-ai)
- [Cosmos 3 Technical Report](https://research.nvidia.com/labs/cosmos-lab/cosmos3/technical-report.pdf)
- [NVIDIA Isaac GR00T Developer Page](https://developer.nvidia.com/isaac/gr00t)
- [GR00T N1 on Hugging Face](https://huggingface.co/nvidia/GR00T-N1.x)
- [V-JEPA 2 Paper (arXiv:2506.09985)](https://arxiv.org/abs/2506.09985)
- [Physical Intelligence (π0)](https://www.physicalintelligence.company/)
- [OpenVLA](https://openvla.github.io/)
- [Awesome World Models for Robots](https://github.com/operator22th/awesome-world-models-for-robots)
