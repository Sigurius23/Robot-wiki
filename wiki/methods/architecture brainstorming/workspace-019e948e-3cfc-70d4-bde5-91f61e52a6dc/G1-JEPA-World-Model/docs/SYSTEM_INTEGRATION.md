# G1-JEPA World Model: Full System Integration Framework

This document defines how the various research components (MinkowskiNet, Slot Attention, DINO, VICReg, VoxFormer, 4D-NVS, WorldRFT, V-JEPA 2, JEPA, CBF) interoperate and the hardware required to sustain them.

## 🔄 The Integrated 4D Loop

The system is now evolved into a **Tethered Object-Centric 4D Spatio-Temporal Hierarchy**.

### 1. The High-Level "Semantic Loop" (0.5 - 1 Hz)
- **Tech:** 3D Gaussian Splatting (3DGS) + VL-JEPA + Slot Attention + DINOv3.
- **Function:** Ingests environment maps and binds user commands to specific "Slots" (objects).

### 2. The Mid-Level "4D Predictive Loop" (5 - 40 Hz)
- **Tech:** **Offboard RTX 5090 (24GB VRAM)** + V-JEPA 2 + MinkowskiNet + 4D-NVS + VICReg + WorldRFT + Tether-Aware MPPI.
- **Function:** 
    - **Tether Physics:** Explicitly penalizes unwrapped yaw ($\theta_{yaw}$) to prevent self-entanglement.
    - **Acoustic-JEPA:** Injects hazards from non-line-of-sight audio cues.
    - **MPPI:** Samples 1024+ trajectories at 40Hz over the Gigabit link.

### 3. The Low-Level "Reactive Loop" (500 Hz)
- **Tech:** **Onboard Orin NX** + FAST-LIO2 + Proprioceptive CBF + Link-Loss Buffer.

---

## 🏗 Required Hardware & Compute Matrix (Tethered Mod)

| Module | Core Hardware | Hardware Feature Used | Minimum Memory | Compute |
| :--- | :--- | :--- | :--- | :--- |
| **G1 Internal** | Orin NX (16GB) | FAST-LIO2 / WBC / CBF | 4.0 GB | Low (Latency Critical) |
| **Offboard Laptop** | **RTX 5090 (24GB VRAM)** | V-JEPA 2 / 3DGS / MPPI | **24.0 GB** | **Saturated (40 Hz)** |
| **Network** | Gigabit Ethernet | Active Tension Spool | N/A | < 1 ms latency |

---

## 🛠 Integration Roadmap: "Tethered-JEPA"

1.  **Mechanical Leash:** Install top-mounted slip ring and active motorized spool.
2.  **Unwrapped Yaw Penalty:** Implement $\lambda_1 (\theta_{yaw})^2$ in the MPPI cost function to automate cable management.
3.  **Kinematic Decay Buffer:** Deploy `TrajectoryBuffer` on the G1 to handle network interruptions.
4.  **Acoustic Uncertainty Cones:** Map audio hazard scores as 3D cones within the Sparse Voxel Memory.
