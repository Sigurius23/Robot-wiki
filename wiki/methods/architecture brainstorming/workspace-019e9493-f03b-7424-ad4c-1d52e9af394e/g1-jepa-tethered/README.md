# G1-JEPA-World-Model: Transitioning from SLAM to Predictive Latent Spaces

This repository serves as a technical brainstorming hub for migrating the **Unitree G1 Humanoid** from traditional geometric SLAM to a mapless **Joint Embedding Predictive Architecture (JEPA)**. 

## 🏗 Core Architecture Components

### 1. Object-Centric Semantic Planning (DINO + Slot Attention)
Instead of metric costmaps, we decompose the scene into discrete, trackable **Slots**.
- **Mechanism:** [DINO](./docs/papers/dino.md) provides unsupervised segmentation masks, and [Slot Attention](./docs/papers/slot_attention.md) extracts objects. Natural language commands are anchored to specific slots.

### 2. Latent MPPI & Energy-Based Constraints (EBC)
Action sequences are optimized in the latent space.
- **Mechanism:** Trajectories that yield high cosine similarity to $s_{nogo}$ (or unsafe slots) receive an infinite energy penalty.

### 3. 4D Sparse Voxel Latent Memory (Inspired by VoxFormer & 3DGS)
Solving for object permanence during rearward navigation.
- **Mechanism:** A 3D sparse voxel grid stores semantic embeddings.
- **New Layer:** **4D Neural Voxel Splatting** for dynamic scene handling and **3D Gaussian Splatting** for photorealistic grounding.

### 4. Safety & Fallback
- **Hamilton-Jacobi Reachability:** Identifying "Latent Failure Sets."
- **Control Barrier Functions (CBF):** 500Hz+ proprioceptive feedback for physical override.

## ⚡ Hardware & Integration
We have mapped the full inter-module communication and the hardware needed to run it.
- **[Full System Integration Framework](./docs/SYSTEM_INTEGRATION.md)**: Compute/RAM analysis and integration pipeline.
- **[Hardware Resource Analysis](./docs/HARDWARE_RESOURCES.md)**: Specific hardware usage on Orin NX.

## 📚 Knowledge Graph & Literature
A structured index of the research driving this project.
- **[Research Index & Interlinks](./docs/papers/README.md)**: Explore papers like **DINO**, **VoxFormer**, **Slot Attention**, and **WorldRFT**.

---
*Note: This project is designed for the Unitree G1 (EDU/Flagship) hardware baseline (Orin NX, 16GB RAM).*
