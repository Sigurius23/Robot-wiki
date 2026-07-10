# G1-JEPA Implementation Roadmap

## Phase 1: Foundation (Current)
- [x] Technical architecture definition.
- [x] Initial repository structure.
- [x] Skeleton for Latent MPPI and Voxel Memory.

## Phase 2: Simulation (Unitree G1 Sim)
- [ ] Implement a lightweight **V-JEPA encoder** (Distilled DINOv2 or SigLIP).
- [ ] Integrate latent planning in Isaac Gym or Gazebo.
  - **Training enhancement:** Add **fractal noise terrain** (Perlin-like multi-octave) to the Isaac Lab terrain generator. From the "Humanoid Parkour Learning" paper (CoRL 2024, [arXiv:2406.10759](https://arxiv.org/abs/2406.10759)) — forces natural foot-raising without hand-designed "feet air time" rewards. Drop-in change, no reward function modification needed. See [docs/papers/humanoid_parkour.md](./docs/papers/humanoid_parkour.md).
  - **D435i sensor noise model:** Reuse the paper's published domain randomization parameters for the Intel RealSense D435i (same camera as our G1) to improve zero-shot sim-to-real transfer.
- [ ] Benchmark "Trajectory Pruning" success rates against virtual "No-Go" zones.

## Phase 3: Hardware Optimization (Jetson Orin NX)
- [ ] Quantize JEPA predictor (FP16/INT8) using **TensorRT**.
- [ ] Implement the **Sparse Voxel Grid** using efficient CUDA kernels to minimize RAM overhead.
- [ ] Calibrate **Uncertainty-Triggered Damping** thresholds on physical terrain.

## Phase 4: Full Deployment
- [ ] Multi-modal fusion: VL-JEPA + 360 LiDAR + CBF Fallback.
- [ ] Real-world testing of backward navigation in cluttered human environments.
- [ ] Open-vocabulary constraint testing ("Avoid the power cables").
