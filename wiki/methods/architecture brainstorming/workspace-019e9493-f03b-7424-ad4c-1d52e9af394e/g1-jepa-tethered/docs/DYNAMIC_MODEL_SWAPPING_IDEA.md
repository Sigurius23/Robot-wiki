# Idea: Dynamic Model Swapping (Smart Select)

> **Status:** Conceptual / Idea Phase (Revised based on multi-agent hardware analysis)
> **Context:** Exploratory architecture for tethered operation using an RTX 5090 Laptop (24GB GDDR7, 64GB DDR5) and Jetson Orin NX (16GB). 
> **OS Requirement:** Ubuntu 22.04+ (Dual-boot or dedicated SSD) to support standard ROS2/NVIDIA robotics tooling (GR00T, TensorRT).

## The Concept

Running every neural network model simultaneously on a 24GB GPU will cause a VRAM out-of-memory (OOM) crash. Instead, we use a **Service-Level Orchestrator** to dynamically switch the active models based on the robot's current behavioral mode.

The laptop's 64GB DDR5-6400 RAM acts as the staging buffer. During a mode switch, the orchestrator triggers a rapid DMA transfer (over the laptop's internal PCIe lanes) to swap the necessary task "heads" into the GPU's 24GB GDDR7 VRAM.

## Core Architectural Rules

1. **Resident Backbone + Swappable Heads:** We do *not* unload everything. We keep a shared perception backbone (e.g., DINOv3 ViT-L/B) and the Voxel Memory resident in VRAM permanently. We only swap the heavy task-specific "heads" (VLA, Reasoner, Predictive models).
2. **Service-Level Orchestration:** Rather than relying on naive PyTorch `model.to('cuda')` swaps which suffer from allocator latency and engine warmup, we run separate long-lived processes (e.g., `nav_service`, `manip_policy_service`, `reasoning_service`). The ROS2 Orchestrator simply switches which service owns the command channel.
3. **Fast Python Swapping (Fallback):** If raw PyTorch swapping is required, CPU tensors must use pinned (page-locked) memory (`param.data.pin_memory()`). This allows DMA transfers to hit 40-60 GB/s, enabling a 6GB model to swap in ~100-150ms.
4. **Safe Swap Posture:** Mode transitions are *never* continuous. Swaps are only triggered when the robot is in a stable, quasi-static configuration (zero velocity, gripper hold). The onboard Jetson Orin NX *always* maintains active locomotion and balance (FAST-LIO2 + CBF).
5. **Peak VRAM Budgeting:** VRAM math must include an additional **~2-3GB activation overhead** per mode to account for KV-caches, activation tensors, and CUDA context, not just static weights.

## Proposed Behavioral Modes

### 1. Navigation & Transit Mode
**Goal:** Move from Point A to Point B safely and quickly. No object manipulation required.
- **Resident (Always On):** DINOv3 Backbone (~2-3GB) + Voxel Memory (~2GB).
- **Active Swapped Models:** LeJEPA (low-res, ~2GB) + A* Planner (~0.5GB).
- **Unloaded/Inactive:** VLA, Heavy Reasoners.
- **Realistic Peak VRAM:** ~9-10 GB.
- **Why:** Extremely safe, leaves massive VRAM headroom (~14GB) for high-frequency control loops.

### 2. Precision Manipulation Mode
**Goal:** Pick and place, tool use, or close-quarters object interaction.
- **Resident (Always On):** DINOv3 Backbone (~2-3GB) + Voxel Memory (~2GB).
- **Active Swapped Models:** Fine-tuned VLA (e.g., GR00T N1.7 3B or PaliGemma, ~6GB weights).
- **Unloaded/Inactive:** LeJEPA, Heavy Reasoners.
- **Realistic Peak VRAM:** ~15-16 GB (Includes ~3GB activation/KV-cache overhead for the VLA).
- **Why:** Focuses compute on high-fidelity visual segmentation and the manipulation policy. Safe within the 24GB limit.

### 3. Deep Exploration / Scene Understanding Mode
**Goal:** Searching for a specific object, mapping a novel room, or responding to a complex semantic query.
- **Resident (Always On):** DINOv3 Backbone (~2-3GB) + Voxel Memory (~2GB).
- **Active Swapped Models:** Cosmos Reason2-2B (~4-5GB weights). *(Note: Cosmos 3 Nano 8B is too risky for 24GB without aggressive NVFP4 quantization).*
- **Unloaded/Inactive:** VLA, LeJEPA.
- **Realistic Peak VRAM:** ~14-16 GB.
- **Why:** Activates a dedicated Visual-Language Model (VLM) to understand the environment while physical tasks are halted.

### 4. Emergency / Safe-Stand Mode
**Goal:** Recover from a tether link drop, hardware thermal throttle, or safety violation.
- **Active Models (Offboard Laptop):** None (Orchestrator halts all command output).
- **Active Models (Onboard Orin NX):** FAST-LIO2 Odometry + CBF / FIRM (Safety Policies).
- **Why:** Reverts completely to the onboard reactive safety stack. The Orin NX handles this effortlessly at >73 FPS, ensuring balance and collision avoidance regardless of the laptop's state.

## ROS2 State Machine Logic

The Orchestrator acts as a ROS2 `LifecycleNode` with strict guard conditions:

```text
NAV → MANIPULATION: Allowed ONLY IF velocity < threshold AND arm in safe pose
ANY → EMERGENCY: Interrupt-driven, immediate, no wait conditions
EMERGENCY → ANY: Requires explicit human confirmation (via ROS2 service call)
```
