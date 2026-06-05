# 4D Spatio-Temporal ConvNets: Minkowski Convolutional Neural Networks

**Paper:** [arXiv:1904.08755v4](https://arxiv.org/abs/1904.08755)  
**Authors:** Christopher Choy, JunYoung Gwak, Silvio Savarese (Stanford University)  
**Core Domain:** High-Dimensional Sparse Convolutions, 4D Perception.

---

## 🔬 Core Contribution
Introduction of **MinkowskiEngine**, an auto-differentiation library for sparse tensors that enables generalized convolutions in high-dimensional spaces (4D+). It allows neural networks to process 3D videos (3D scans + time) as a single 4D spatio-temporal volume rather than frame-by-frame.

## 🛠 Relevant Mechanisms for G1-JEPA
*   **Generalized Sparse Convolution:** Efficiently processes non-empty voxels in 4D. This is critical for the G1’s Orin NX, as it avoids computing empty space.
*   **Hybrid Kernel:** A non-hypercubic kernel that combines a spatial cubic kernel (to capture geometry) with a temporal cross-shaped kernel (to capture motion). This reduces parameter count while maintaining spatio-temporal consistency.
*   **Trilateral-Stationary CRF:** A Conditional Random Field that enforces consistency across 3D space, 1D time, and 3D color (7D). It ensures that stationary objects remain stationary in the robot's "mind" across frames.

## 🔗 Interlinks to Project Components
- [x] **JEPA Encoder:** MinkowskiNet provides the backbone for the JEPA encoder to ingest a *sequence* of G1 sensor frames (LiDAR/Depth) into a unified 4D latent representation.
- [x] **Voxel Memory:** Directly informs the transition from 3D static grids to 4D spatio-temporal sparse tensors.
- [ ] **Dynamic Obstacle Tracking:** The 4D convolution natively captures motion vectors, assisting the world model in predicting the trajectories of moving humans/objects.

## 🚀 Actionable Integration Plan
1.  **Backbone Swap:** Use a **Minkowski ResNet-14** as the primary spatio-temporal encoder for the G1's vision-depth stream.
2.  **Temporal Buffer:** Implement a sliding window of 4D sparse tensors in the Orin NX RAM (e.g., last 10 frames) to be processed by a single 4D convolution pass.
3.  **Stationarity Constraint:** Use the Trilateral-Stationary logic to reduce "spatial drift" in the robot's latent memory.
