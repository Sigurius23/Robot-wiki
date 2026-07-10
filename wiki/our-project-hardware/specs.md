---
title: Our Project Hardware
tags: [hardware, specs, setup]
date_updated: 2026-06-04
---

# Our Project Hardware Specifications

This document outlines the hardware specifications and compute infrastructure available for this project. These resources define our engineering constraints for policy training, simulation, and real-time humanoid inference.

---

## 1. Robotic Platform

### Unitree G1 Humanoid Robot (Education/EDU Edition)
* **Dexterous Hands**: 5-finger dexterous hands with up to 33 optional tactile sensors per hand.
* **Degrees of Freedom (DoF)**: Full-body joint articulation.
* **Onboard Compute System**: Dual-computing architecture delivering 100 TOPS of AI processing power:
  * **Arm® Cortex®-A78AE (8-Core CPU)**: Acting as primary processor for low-level real-time motion control, joint stability, and motor feedback loop.
  * **NVIDIA Jetson Orin NX (16GB)**: Processing perception algorithms, machine learning models, visual tracking, and sensor fusion directly on the robot.
* **Connected Sensor Suite**:
  * **3D LiDAR**: Livox Mid-360 mounted on the head (360-degree spatial mapping).
  * **Depth Camera**: Intel RealSense D435i (point-cloud and visual recognition).
  * **Audio Array**: Built-in 4-microphone array for directional voice capture.
  * **Motion Sensors**: High-frequency Inertial Measurement Units (IMUs) tracking equilibrium.
  * **Motor Feedback**: Dual high-frequency encoders on each joint tracking position and force.

---

### 1.1 Competitor Comparison: Humanoid Robots

#### DEEP Robotics DR02
* **Manufacturer**: DEEP Robotics (杭州云深处科技有限公司, China).
* **Height / Weight**: 175 cm / 65 kg.
* **Degrees of Freedom**: ~28 joints (proprietary modular actuators).
* **Onboard Compute**: 275 TOPS — comparable to Jetson AGX Orin-class hardware. Exact chip undisclosed.
* **Sensors**: Multi-modal fusion — LiDAR + depth cameras + wide-angle cameras + IMU.
* **Control Architecture**: Hierarchical — high-level task planner + Whole-Body Control (WBC) + RL-based gait adaptation. Proprietary, no published paper.
* **Locomotion**: 1.5 m/s walk / 4 m/s run. Climbs 20° slopes.
* **Manipulation**: 10 kg payload. Human-compatible end effectors.
* **Environmental Rating**: **IP66** — first humanoid rated for rain, high humidity, and dust. Operates –20°C to +55°C.
* **Key Differentiator**: Industrial ruggedness, not AI/software capability. Modular quick-detach limbs for field maintenance.
* **Relevance to Our Project**: The DR02's hierarchical architecture (high-level planner → WBC) mirrors our tether design (Cosmos/GR00T → WBC). The 275 TOPS onboard compute suggests our targeted untethered hardware (Jetson AGX Orin, 275 TOPS) is in the right performance tier. However, DR02's control stack is proprietary — we're building ours openly.

#### Unitree H1 (Parkour Paper Reference)
* **Manufacturer**: Unitree Robotics — same manufacturer as our G1.
* **Key Capability**: The "Humanoid Parkour Learning" paper (CoRL 2024, [arXiv:2406.10759](https://arxiv.org/abs/2406.10759)) demonstrated end-to-end vision-based parkour on the H1 — jumping 0.42m, leaping 0.8m, running 1.8 m/s — using only an Intel RealSense D435i depth camera and onboard CPU inference. This is directly transferable methodology for our G1. See [docs/papers/humanoid_parkour.md](../methods/architecture%20brainstorming/workspace-019e9493-f03b-7424-ad4c-1d52e9af394e/g1-jepa-tethered/docs/papers/humanoid_parkour.md).

---

## 2. Local Workstation (Development & Inference)

### Mobile Workstation Laptop
* **GPU**: NVIDIA RTX 5090 (24GB VRAM).
  * *Role*: Local physics simulation (e.g. Isaac Sim / MuJoCo), policy debugging, real-world low-latency inference, and model deployment.
* **System Memory**: 64GB RAM.
* **Storage**: 2TB NVMe SSD.
* **Role in Pipeline**: 
  * Running the main control loop for the G1.
  * Real-time vision-language-action (VLA) model inference.
  * Direct teleoperation or policy deployment (Sim-to-Real).

---

## 3. High-Performance Computing (HPC) Cluster

### Remote Training Cluster
* **Access**: Batch scheduling.
* **Capabilities**: Large-scale multi-GPU training nodes.
* **Constraints**: **Training only**. No real-time connection to the physical robot, meaning it cannot be used for inference or live policy execution.
* **Role in Pipeline**:
  * Running reinforcement learning training scripts (e.g., Isaac Lab, Legged Gym).
  * Pre-training representation learning models or world models.
  * Offline evaluation and parameter sweeps.
