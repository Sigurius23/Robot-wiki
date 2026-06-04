---
title: Our Project Hardware
tags: [hardware, specs, setup]
date_updated: 2026-06-04
---

# Our Project Hardware Specifications

This document outlines the hardware specifications and compute infrastructure available for this project. These resources define our engineering constraints for policy training, simulation, and real-time humanoid inference.

---

## 1. Robotic Platform

### Unitree G1 Humanoid Robot (Education Edition)
* **Hands**: 5-finger dexterous hands (Education Edition).
* **Degrees of Freedom (DoF)**: Full-body joint articulation.
* **Onboard Compute**: Low-power onboard PC (primarily used for running the low-level motor controller, joint communication, and basic sensor streaming).

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
