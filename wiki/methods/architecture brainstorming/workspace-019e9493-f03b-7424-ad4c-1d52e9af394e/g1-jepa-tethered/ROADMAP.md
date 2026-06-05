# G1-JEPA Implementation Roadmap

## Phase 1: Foundation (Current)
- [x] Technical architecture definition.
- [x] Initial repository structure.
- [x] Skeleton for Latent MPPI and Voxel Memory.

## Phase 2: Simulation (Unitree G1 Sim)
- [ ] Implement a lightweight **V-JEPA encoder** (Distilled DINOv2 or SigLIP).
- [ ] Integrate latent planning in Isaac Gym or Gazebo.
- [ ] Benchmark "Trajectory Pruning" success rates against virtual "No-Go" zones.

## Phase 3: Hardware Optimization (Jetson Orin NX)
- [ ] Quantize JEPA predictor (FP16/INT8) using **TensorRT**.
- [ ] Implement the **Sparse Voxel Grid** using efficient CUDA kernels to minimize RAM overhead.
- [ ] Calibrate **Uncertainty-Triggered Damping** thresholds on physical terrain.

## Phase 4: Full Deployment
- [ ] Multi-modal fusion: VL-JEPA + 360 LiDAR + CBF Fallback.
- [ ] Real-world testing of backward navigation in cluttered human environments.
- [ ] Open-vocabulary constraint testing ("Avoid the power cables").
