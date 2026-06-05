# Hardware Requirements & System Integration Framework

This document outlines the computational budget for the G1-JEPA World Model and the integration pipeline for the NVIDIA Jetson Orin NX (onboard) and the RTX 5090 Laptop (offboard).

## 🖥 Hardware Profile: Unitree G1 (EDU/Flagship)

### Onboard: Jetson Orin NX (16GB)
- **AI Performance:** 100 TOPS (Standard) / 157 TOPS (Super Mode @ 40W)
- **Memory:** 16GB LPDDR5 (Unified)
- **Primary Tasks:** FAST-LIO2, WBC, CBF Safety, Network Watchdog.

### Offboard: RTX 5090 Laptop (24GB)
- **AI Performance:** High-throughput Ampere/Blackwell architecture.
- **VRAM:** 24GB GDDR7 (Reference: [HardwareLuxx](https://www.hardwareluxx.de/index.php/news/hardware/grafikkarten/65186-3-gb-chips-sei-dank-geforce-rtx-5090-fuer-laptops-soll-24-gb-vram-erhalten.html))
- **Primary Tasks:** DINOv3 (ViT-L), V-JEPA 2, 4D-NVS, MPPI (1024 samples), Acoustic-JEPA.

---

## 📊 Offboard Compute Budget (RTX 5090 - 24GB VRAM)

| Component | Model Backbone | VRAM Usage | TOPS Usage | Frequency |
| :--- | :--- | :--- | :--- | :--- |
| **Perception** | DINOv3 (ViT-L Distilled) | ~6.0 GB | High | 40 Hz |
| **World Model** | V-JEPA 2 (ViT-g) | ~8.0 GB | High | 40 Hz |
| **4D Memory** | 4D-NVS (HexPlane) | ~4.0 GB | Medium | 40 Hz |
| **Planner** | MPPI (1024 samples) | ~3.0 GB | High | 40 Hz |
| **Acoustic-JEPA** | 16kHz Latent Audio | ~1.0 GB | Low | 40 Hz |
| **System/OS** | Linux / CUDA Overhead | ~2.0 GB | N/A | N/A |
| **TOTAL** | | **~24.0 GB** | **~95%** | **SATURATED** |

*Note: Achieving 40Hz with these models requires extreme optimization (TensorRT INT8) and potentially dropping the batch size of the MPPI planner if VRAM limits are hit during long-horizon rollouts.*

---

## 🏗 System Integration Framework

```mermaid
graph TD
    %% Sensory Input
    A[G1 Sensors] -- Gigabit Tether -- > B[RTX 5090 Planner]
    
    %% Offboard Logic
    B --> C[DINOv3 / Acoustic-JEPA]
    C --> D[4D Voxel Memory]
    D --> E[V-JEPA 2 Predictor]
    E --> F[Tether-Aware MPPI]
    
    %% Feedback Loop
    F -- 500ms Trajectory Buffer -- > G[G1 Orin NX]
    G --> H[FAST-LIO2 / WBC]
    H --> I[Actuators]
```

---

## 🛠 Hardware Optimization Strategy

1.  **VRAM Caching:** To fit into 24GB, we use **Activation Checkpointing** and **Weight Quantization (INT8/FP8)**.
2.  **Gigabit Slip Ring:** Essential for maintaining the 1ms latency required for the 40Hz control loop.
3.  **Dynamic Decoupling:** The robot handles high-frequency balance (500Hz) while the laptop handles the future (40Hz).
