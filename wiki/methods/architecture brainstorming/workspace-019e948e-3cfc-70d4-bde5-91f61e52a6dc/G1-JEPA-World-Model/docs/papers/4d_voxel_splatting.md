# 4D Neural Voxel Splatting: Dynamic Scene Rendering with Voxelized Gaussian Splatting

**Paper:** [arXiv:2511.00560](https://arxiv.org/abs/2511.00560)  
**Core Domain:** Dynamic Scene Representation, 4D Gaussian Splatting, Edge AI.

---

## 🔬 Core Contribution
Proposed **4D Neural Voxel Splatting (4D-NVS)**, which extends voxelized representations to the temporal domain. It decouples spatial structure from temporal dynamics by generating "Neural Gaussians" on-demand from persistent voxel anchors and applying unified deformations.

## 🛠 Relevant Mechanisms for G1-JEPA
*   **Decoupled Representation:** Separates the static background (persistent voxels) from the dynamic changes (temporal deformation). This allows the G1 to "remember" the static floor while "hallucinating" how a moving person will change position.
*   **HexPlane Temporal Corrections:** Uses a decomposed 4D encoding (HexPlane) to capture temporal dynamics efficiently. This is much more memory-efficient than storing a full 3D grid for every timestamp.
*   **Resource Efficiency:** Specifically mentions suitability for **NVIDIA Jetson (4-16GB)** devices. It achieves $\mathcal{O}(fV + F)$ memory complexity, making it ideal for the G1's 16GB Orin NX.

## 🔗 Interlinks to Project Components
- [x] **Voxel Memory (Stage 2):** Provides the "Densification" logic for the G1’s sparse latent memory. It allows the model to "splat" latent features back into a queryable 4D volume.
- [x] **Object Permanence:** The decoupled persistent anchors ensure the robot doesn't "forget" the geometry of a room just because things are moving within it.
- [x] **Predictive Simulation:** The temporal deformation field serves as a differentiable prior for the JEPA predictor's future state forecasts.

## 🚀 Actionable Integration Plan
1.  **Voxel Anchors:** Initialize the G1's local memory grid as **Persistent Voxel Anchors** (from static depth data).
2.  **Temporal Encoding:** Use the **HexPlane** logic to encode temporal features into the 4D sparse voxel grid.
3.  **On-Demand Splatting:** Use the lightweight MLP to generate predicted Gaussian features for "blind" regions, enabling high-fidelity collision checking in the latent space.
