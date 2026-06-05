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

## 📝 Contribution Guide
When adding a new paper:
1. Copy the `PAPER_TEMPLATE.md`.
2. Save as `[paper_name].md`.
3. Update this `README.md` index to link the paper to the relevant architectural component.
