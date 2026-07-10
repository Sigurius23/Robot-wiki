# Literature Knowledge Graph: G1-JEPA World Model

This directory contains summaries of key research papers and industry breakthroughs, cross-referenced with the core components of the G1 transition project.

## 🗺 Knowledge Index (By Component)

### 🧠 1. Latent Memory & Object Permanence
*Systems for maintaining world state in unobserved/blind regions.*
- **[VoxFormer (2023)](./voxformer.md):** Sparse voxel transformers for 3D semantic scene completion. Essential for G1's rear blind spot hallucination.
- **[3D Gaussian Splatting (2025 Industry Report)](./3dgs_mapping.md):** High-fidelity environment capture for "Real-to-Sim" training.
- **[4D Neural Voxel Splatting (2025)](./4d_voxel_splatting.md):** Dynamic scene rendering using voxelized Gaussian splatting. Decouples static geometry from temporal motion.

### 🧭 2. Mapless Planning & MPPI
*Generating optimal trajectories within abstract latent embeddings.*
- **[WorldRFT (2025)](./world_rft.md):** Reinforcement fine-tuning for latent world models. Hierarchical planning and collision-aware rewards.
- **[V-JEPA 2 (2025)](./vjepa2.md):** Action-conditioned video models for zero-shot planning and prediction using internet-scale data.
- **[Humanoid Parkour Learning (CoRL 2024)](./humanoid_parkour.md):** End-to-end vision-based RL for jumping, leaping, and climbing — no motion priors needed. Fractal noise terrain curriculum + DAgger distillation. Runs on CPU. Same D435i camera as our G1.
- **[Tether Physics Prediction (Internal Strategy)](../SYSTEM_INTEGRATION.md):** Using unwrapped yaw penalties and tension-aware cost functions to prevent entanglement.

### 🛡 3. Safety Filters & Reachability
*Enforcing constraints and preventing falls using Hamilton-Jacobi or CBFs.*
- **[Link-Loss Trajectory Buffering (Internal Strategy)](../src/tether_safety.py):** 500ms kinematic decay buffer for graceful network failure recovery.

### 👁 4. High-Dimensional Perception & JEPA Encoders
*Architecture for processing multimodal sensor streams.*
- **[Minkowski Spatio-Temporal ConvNets (2019)](./minkowski_net.md):** 4D Sparse convolutions for unified space-time processing.
- **[Slot Attention (2020)](./slot_attention.md):** Object-centric learning to decompose scenes into discrete, trackable entities.
- **[DINOv3: Self-Supervised ViT (2025)](./dino.md):** Dense features with Gram-anchoring. Ideal for unsupervised segmentation.

---

---

## 🏗 Architecture Design Documents
*Cross-cutting design documents for the G1 pipeline.*

### Industry Research & Integration
- **[Cosmos 3 & VLA Research Synthesis](../COSMOS3_AND_VLA_RESEARCH.md):** How Cosmos 3, GR00T, π0, and current VLAs fit our G1 project.
- **[How Cosmos 3 Works](../HOW_COSMOS3_WORKS.md):** Practical guide to Cosmos 3 architecture, APIs, and running it on RTX 5090.
- **[Action Space Adapter](../ACTION_SPACE_ADAPTER.md):** Mapping Cosmos 3's 29D AgiBot humanoid format → G1's 43 DoF.
- **[LLM & VLM Roles — GLM-5.1 & Gemma 4 12B](../LLM_AND_VLM_ROLES.md):** Where general-purpose LLMs/VLMs fit as task planners, scene describers, and orchestrators. 4 new architecture variations. VRAM co-residency matrix.
- **[VRAM Measurements — Real Inference Footprints](../VRAM_MEASUREMENTS.md):** 🔬 Researched VRAM numbers for all models (ViT-g, V-JEPA 2, MinkowskiNet, Cosmos 3 NVFP4). Estimates vs. actuals with corrected budgets. **Canonical source for all project VRAM numbers.**
- **[VRAM Quick Reference Card](../VRAM_QUICKREF.md):** 🔢 One-page lookup of all canonical VRAM numbers. Updated from VRAM_MEASUREMENTS.md.
- **[Hardware Risk Register](../HARDWARE_RISK_REGISTER.md):** 🛡️ Failure modes, fallback strategies, and recovery procedures for every variation. VRAM overflow, link loss, thermal throttle, model swapping, sequential execution.

### Pipeline Architecture Variations
- **[Architecture Variations](../ARCHITECTURE_VARIATIONS.md):** **10 pipeline diagrams** — Pure JEPA, Cosmos-Centric, GR00T-Centric, Hybrids, Distilled, End-to-End VLA, Full NVIDIA Stack. Comparison matrix and migration pathways.
- **[Architecture Variations — Mermaid.js](../ARCHITECTURE_VARIATIONS_MERMAID.md):** 🎨 **Rendered diagrams** of the 3 most important variations (Baseline JEPA, Cosmos-Centric, Cosmos+GR00T Hybrid) in Mermaid flowchart syntax. Side-by-side comparison chart. Renders natively in GitHub and Obsidian.
- **[System Integration Framework](../SYSTEM_INTEGRATION.md):** Original tethered 4D loop design with compute matrix.
- **[Transition Plan](../TRANSITION_PLAN.md):** From SLAM to mapless JEPA — no-go zones in latent space.
- **[Validation Plan](../VALIDATION_PLAN.md):** 3-stage sim-to-real validation strategy.
- **[Hardware Resources](../HARDWARE_RESOURCES.md):** Orin NX memory and compute budget.

---

## 📝 Contribution Guide
When adding a new paper:
1. Copy the `PAPER_TEMPLATE.md`.
2. Save as `[paper_name].md`.
3. Update this `README.md` index to link the paper to the relevant architectural component.
