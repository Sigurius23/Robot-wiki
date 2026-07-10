# Dynamic Orchestration Architecture (V2)

> **Status:** Architecture Design Document (V2)
> **Context:** Advanced task-mode orchestration for a tethered Unitree G1 robot utilizing an RTX 5090 Laptop (24GB GDDR7, 64GB DDR5) and Jetson Orin NX (16GB).
> **OS Requirement:** Ubuntu 22.04+ (dual-boot or dedicated SSD) to support `isaac_ros_dnn_inference`, TensorRT, and standard ROS2 robotics tooling.

## 1. Purpose and Design Goals
Design a production-grade orchestration system that dynamically switches neural network policies based on the robot's current task. By using precompiled TensorRT engines exposed as ROS2 services (rather than naive PyTorch tensor swapping), the system avoids VRAM OOM crashes, hides warmup latency via shadow inference, and guarantees an onboard safety floor.

## 2. System Assumptions and Non-Goals

### Architectural Assumptions
- **Control Split:** The high-level Vision-Language-Action (VLA) policy runs offboard at a low frequency (e.g., 2.5 Hz). The G1's local SONIC stack decodes these latent motion tokens into full-body joint commands at high frequency (50 Hz).
- **Deployment Primitive:** We rely on `isaac_ros_dnn_inference` for NITROS-compatible zero-copy communication.

### Non-Goals (Things We Will Not Do)
- **NO** live authority transfer during unstable locomotion.
- **NO** mode switch while the arm is mid-contact unless explicitly allowed by the state machine.
- **NO** Wi-Fi-only operation for high-risk, precision manipulation tasks.
- **NO** heavy-reasoner loading during active walking.
- **NO** dependence on the offboard laptop GPU for emergency stops, balancing, or collision avoidance.

---

## 3. 3-Tier Runtime Architecture

Instead of treating the system as a monolithic swap, memory is managed across three distinct tiers:

### Resident Tier (GPU VRAM - 24GB RTX 5090)
*Models permanently loaded into VRAM that never swap.*
- **Perception Backbone:** DINOv3 (ViT-B or ViT-L).
- **Spatial Memory:** Voxel map / MinkowskiNet.
- **Planners:** A* or lightweight MPC.
- **Auxiliary Monitor:** Lightweight offboard fallback perception to monitor swap health.
- **Infrastructure:** Command Mux client and sensor preprocessors.

### Warm Standby (Host CPU RAM - 64GB DDR5)
*The candidate service preparing to take authority.*
- Weights staged in host RAM (pinned memory where useful).
- Engine metadata preloaded.
- Candidate service process spawned.
- Shadow inference buffers allocated.

### Cold Storage (NVMe / RAM)
*Inactive models.*
- Alternate policies and LoRAs.
- Debug engines.
- Known-good rollback versions (critical for production robotics).
- Offline evaluation models.

---

## 4. 6-Mode State Machine

| Mode | Active Models / Focus | Corrected Peak VRAM |
|---|---|---|
| **0: Safe/Local** | Orin NX only. Local safety loops (FAST-LIO2, CBF). | 0GB (Offboard) |
| **1: Transit** | Resident perception + Planners. | ~6–7GB |
| **2: Approach/Pregrasp**| Transit stack + High-res wrist cam + Prewarm Manip Policy. | ~8–9GB |
| **3: Manipulation** | Resident perception + GR00T N1.7 (TRT) / VLA. | ~14–16GB |
| **4: Search/Query** | Resident perception + Cosmos-Reason2-2B (W4A16). | ~14–16GB |
| **5: Teach/Teleop** | Resident perception + Logging / Dataset export. | ~8GB |

*(Note: GR00T N1.7 utilizes the Cosmos-Reason2-2B backbone and a Diffusion head, consuming ~10-12GB at FP16. For Mode 4, Cosmos-Reason2-2B **must** be W4A16 quantized via vLLM to safely fit the 24GB budget).*

### Example State Transition: Mode 2 (Approach) → Mode 3 (Manipulation)
**Mode 2 Entry Criteria:**
- Target object identified.
- Transit path nearly complete.
- Wrist/head perception active.
- Manipulation candidate service warmup initiated.

**Exit to Mode 3 Criteria:**
- Object confidence > threshold.
- Valid grasp pose identified.
- Robot posture is completely stable.
- Manipulation engine satisfies the Readiness Contract (see Section 6).
- Tether link is healthy.

**Fallback:**
- If object confidence drops, return to Mode 1 (Transit) or Mode 4 (Search).
- If candidate warmup fails, hold pose, retry, or abort to Mode 0.

### Degraded Submodes
To avoid a binary "working vs. safe-stand" system, degraded modes allow partial operation:
- **Transit-Degraded:** Reduced speed due to a lost perception stream or network jitter.
- **Manip-Degraded:** Base locked, arm movement only (triggered by GPU thermal throttle).

---

## 5. Command Authority Matrix & Safety Policy

The **Command Mux** explicitly defines which subsystem has authority over robot hardware.

| Subsystem | Allowed Controllers | Priority | Handoff Conditions | Fallback Owner |
|---|---|---|---|---|
| **Base Velocity** | Orin NX, A* Planner | 1. Orin (Safety)<br>2. Offboard Planner | Stable posture / Zero velocity | Orin NX |
| **Arm / Gripper** | VLA (Mode 3), Teleop | 1. Offboard VLA | Confident target lock | Safe Hold |
| **Torso / Head** | Mode 1, Mode 4 | 1. Offboard Planner | N/A | Safe Hold |
| **Global Halt** | Orin NX, Watchdog, Human E-Stop | 1. Human E-Stop<br>2. Orin NX | Immediate | E-Stop / Orin |

---

## 6. Transition Mechanics & Readiness

Transitions use **Shadow Inference** and a strict **Readiness Contract** rather than fixed time delays.

### The Readiness Contract
Before the Orchestrator promotes a candidate service to active authority, the service must expose and satisfy:
- `engine_loaded` == True
- `warmed_up` == True
- `input_stream_valid` == True
- `output_schema_valid` == True
- `latency_ok` (below target ms threshold)
- `confidence_ok` (policy output confidence > threshold)
- `watchdog_ok` (no thermal/memory flags)

### Shadow Inference
During a mode handoff (e.g., Mode 2 → Mode 3):
1. Keep the current controller in charge.
2. Start the candidate service (e.g., GR00T VLA).
3. Feed the candidate the same sensor observations.
4. Run in parallel until the **Readiness Contract** is satisfied (typically a few hundred milliseconds).
5. Promote candidate; retire old service to Warm Standby or Cold Storage.

---

## 7. LoRA Hot-Swap Strategy (Alternative)

**Concept:** Maintain a frozen foundation model backbone and hot-swap tiny (<200MB) LoRA adapters to change task behaviors in <10ms.

**WARNING:** LoRA hot-swapping is preferred *only* for closely related tasks sharing a common backbone, tokenizer, and action interface. Distinct architectures or sensor schemas must remain as separate TensorRT engines.

---

## 8. Tethering and Communications

- **Physical Link:** USB-C Gigabit Ethernet (indoor/deterministic) or Wi-Fi 6E M.2 (outdoor/130Mbps+).
- **Transport Policy:** Command channels must be explicitly separated from video/logging streams. QoS policies ensure safety topics are reliable, while image streams are best-effort/compressed.
- **Time Sync:** Precision Time Protocol (PTP) is required. Stale frames (>50ms) are explicitly dropped to prevent ghost-actions.

---

## 9. Failure Mode Matrix

| Failure | Consequence & Recovery |
|---|---|
| **OOM / Engine Crash** | Isolate via separate CUDA contexts. Fallback to Mode 0 (Orin NX takes over). |
| **Thermal Throttle (>85°C)** | Degrade to Mode 1 (Transit) or Manip-Degraded. Slow down inference frequency. |
| **Network Dropout** | Orin NX immediately assumes control. Arm freezes and returns to safe pose. |
| **Model Corruption** | Known-good rollback version loaded from Cold Storage. |

---

## 10. Teach / Teleop Data Pipeline (Mode 5)

Data collection is strictly for the `UNITREE_G1_SONIC` embodiment pipeline. 

**Dataset Hygiene:**
- Record precise sensor timestamps, calibration snapshots, robot state logs, operator commands, and success/failure labels.
- *Note on Fine-Tuning:* Standard GR00T fine-tuning requires ~25GB+ VRAM. This cannot run natively on the 24GB RTX 5090 at full precision. Mode 5 is strictly for **Capture / Validate / Replay**, with actual fine-tuning deferred to a cloud cluster (or run locally via `--no-tune_diffusion_model`).

---

## 11. Validation & Benchmarks

Prior to deployment, the following metrics must be profiled:
- Cold start vs. Warm start latency.
- Promotion latency (time to satisfy Readiness Contract).
- Peak VRAM per mode (including CUDA contexts/activations).
- Network dropout recovery time.
- Failure-to-safe time (Orin NX takeover latency).

---

## 12. Future Upgrade Path

- **Jetson Thor:** Delivers up to 128GB LPDDR5X, eliminating the need for a tethered laptop. The entire Orchestration architecture can run purely onboard.
- **Cosmos 3:** Future upgrade for Mode 4 (Search/Query), enabling unified physical reasoning, prediction, and action generation within a single model block, superseding the Cosmos-Reason2-2B implementation.
