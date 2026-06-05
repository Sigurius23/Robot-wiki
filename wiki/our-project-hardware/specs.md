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
