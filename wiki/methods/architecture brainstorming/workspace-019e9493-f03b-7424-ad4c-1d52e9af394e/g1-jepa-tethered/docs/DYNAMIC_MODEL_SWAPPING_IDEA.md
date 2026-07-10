# Idea: Dynamic Model Swapping (Smart Select)

> **Status:** Conceptual / Idea Phase
> **Context:** This is an exploratory idea for when/if the robot is tethered to a high-end compute node (like an RTX 5090 Laptop with 24GB VRAM and 64GB CPU RAM).

## The Concept

Instead of trying to run every neural network model simultaneously and risking a VRAM out-of-memory (OOM) crash, we can design a **"Lifecycle Orchestrator"** node. 

This node acts as a "Smart Select" system. It keeps all model weights staged in the much larger CPU RAM (64GB) and dynamically swaps them into the GPU's VRAM (24GB) over the PCIe bus depending on the robot's current behavioral mode.

This ensures the robot always has the absolute best models loaded for the specific task it is currently performing, while staying safely under the 24GB VRAM limit.

## Proposed Behavioral Modes

### 1. Navigation & Transit Mode
**Goal:** Move from Point A to Point B safely and quickly. No object manipulation required.
- **Active Models (GPU):** MinkowskiNet Voxel Memory (~2GB) + A* Planner (~0.5GB) + LeJEPA (running at low resolution, ~2GB).
- **Unloaded to CPU:** VLA (GR00T/PaliGemma), DINOv3 (high-res).
- **VRAM Footprint:** ~4.5 GB.
- **Why:** Extremely safe, low latency, and leaves plenty of compute headroom for high-frequency control loops.

### 2. Precision Manipulation Mode
**Goal:** Pick and place, tool use, or close-quarters object interaction.
- **Active Models (GPU):** DINOv3 Perception (~5GB) + Fine-tuned VLA (GR00T or PaliGemma, ~6GB) + Voxel Memory (~2GB).
- **Unloaded to CPU:** LeJEPA (Predictive world model).
- **VRAM Footprint:** ~13 GB.
- **Why:** Focuses all compute on high-fidelity visual segmentation (DINOv3) and the manipulation policy (VLA).

### 3. Deep Exploration / Scene Understanding Mode
**Goal:** Searching for a specific object, mapping a novel room, or responding to a complex semantic query from a user.
- **Active Models (GPU):** Cosmos 3 Reasoner (~8GB) + DINOv3 (~5GB) + Voxel Memory (~2GB).
- **Unloaded to CPU:** VLA, LeJEPA.
- **VRAM Footprint:** ~15 GB.
- **Why:** Activates the heaviest visual-language reasoning models to understand the environment, while halting complex physical movements.

### 4. Emergency / Safe-Stand Mode
**Goal:** Recover from a tether link drop, hardware thermal throttle, or safety violation.
- **Active Models (Offboard GPU):** None (All offboard models pause/unload).
- **Active Models (Onboard Orin NX):** FAST-LIO2 Odometry + CBF / FIRM (Safety Policies).
- **Why:** Reverts completely to the onboard reactive safety stack until normal operation can be restored.

## The Swap Mechanism

- **PCIe 4.0 Transfer:** Transferring a ~5GB to 8GB model from CPU RAM to GPU VRAM takes approximately 1 to 2 seconds over a PCIe 4.0 x16 connection. 
- **The "Freeze":** During this 1-2 second transition, the robot would need to perform a brief "safe stand" while its brain reconfigures itself for the new mode.
- **Implementation:** This can be built using standard PyTorch `model.to('cpu')` and `model.to('cuda')` calls, orchestrated via a ROS 2 lifecycle node state machine.
