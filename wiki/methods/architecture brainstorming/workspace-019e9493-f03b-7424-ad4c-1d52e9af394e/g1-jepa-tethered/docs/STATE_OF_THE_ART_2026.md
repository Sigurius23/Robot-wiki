# State of the Art 2026: Hybrid-Modular vs. End-to-End

> **Status:** Strategic Analysis
> **Context:** An analysis comparing our V2 Dynamic Orchestration architecture (RTX 5090 + Orin NX) against the absolute cutting-edge robotics frontier in 2026 (Figure Helix, Physical Intelligence π0).

## 1. The Two Paradigms of 2026

The robotics industry has fractured into two distinct architectural approaches for Vision-Language-Action (VLA) deployment:

### Camp A: End-to-End Whole-Body Control (The Frontier)
Represented by models like **Figure's Helix** and **Physical Intelligence's π0**.
- **How it works:** A single neural network maps raw multi-view camera feeds and natural language directly into 50Hz whole-body joint commands.
- **The Catch:** Requires massive, proprietary datasets (thousands of robot-specific demonstrations), massive compute (Jetson Thor or multi-GPU server), and offers zero debuggability if the robot makes a mistake.

### Camp B: Hybrid-Modular (Our Architecture)
- **How it works:** Uses foundation models for high-level semantic reasoning (DINOv3, GR00T, Cosmos), but relies on a local, classical controller (SONIC, FAST-LIO2, CBF) to decode those latent commands into high-frequency balance and locomotion.
- **Why we chose it:** It is the *only* viable path for a team with one robot, a 24GB VRAM ceiling, and no massive teleop dataset. It provides mathematical safety guarantees for balance, while still leveraging SOTA vision and reasoning.

---

## 2. Three Missing Concepts to Push Toward SOTA

While our V2 architecture is highly optimized for our hardware, the absolute SOTA uses three techniques we should aim to adopt:

1. **Flow Matching Action Decoders (over Diffusion):** The π0 model dominates benchmarks because it uses a *flow matching* action decoder instead of diffusion (like GR00T N1.7). Flow matching converges faster with fewer denoising steps, drastically cutting inference latency. We should look to upgrade the SONIC decoder to flow matching.
2. **Action Chunking:** Instead of predicting one action per step, the VLA should emit a "chunk" of future actions (e.g., 8–50 steps). The robot executes these open-loop while the next chunk computes, solving the stability issues caused by low-frequency (2.5Hz) VLA inference.
3. **World Model Planning:** Currently, our Mode 4 uses Cosmos-Reason2-2B to *answer questions*. The frontier uses models like Cosmos Video Foundation Model or Genie 2 to *simulate the physics of a planned action* before the robot executes it.

---

## 3. The Two Blueprints

Based on the 2026 hardware landscape, here are the two paths forward for the G1:

### Blueprint 1: Best Possible on Current Hardware (Our Target)
**Hardware:** Unitree G1 + Orin NX (onboard) + RTX 5090 Laptop (tethered via built-in 5GbE RJ45 port).
- **Onboard (Orin NX):** Balance, E-Stop, FAST-LIO2, CBF watchdogs.
- **Offboard (RTX 5090):** Runs the V2 Orchestrator using TensorRT engines.
- **Resident VRAM:** DINOv3 (ViT-B), Voxel Map.
- **Swapped VRAM:** GR00T N1.7 (3B) manipulation policy OR Cosmos-Reason2-2B (W4A16) reasoning assistant.
- **Tether:** Use the Alienware's native 5 Gigabit Ethernet RJ45 port for deterministic, zero-jitter telemetry, rather than a USB dongle.

### Blueprint 2: Absolute 2026 SOTA (The Upgrade Path)
**Hardware:** Unitree G1 + Jetson Thor (onboard).
- **Architecture:** Eliminate the tethered laptop entirely. The 128GB LPDDR5X RAM on Jetson Thor allows the entire orchestrator, perception backbone, and a large VLA to run natively inside the robot's chest.
- **Model:** Train an end-to-end, flow-matching VLA (similar to π0 or an advanced UnifoLM-VLA-0 variant) using a massive dataset collected from our Mode 5 (Teach/Teleop) pipeline.
- **Result:** Fully autonomous, untethered, whole-body end-to-end control.
