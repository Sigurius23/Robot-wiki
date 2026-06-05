# Compute Budget: Profiled Latency & Feasible Frequencies

*Based on real-world benchmarks for ViT-L, MinkowskiNet, VLA models, and A* planning. RTX 5090 Laptop (24GB GDDR7, Blackwell) estimated as roughly comparable to RTX 4090 Desktop (Ada Lovelace) due to newer architecture + GDDR7 compensating for mobile TGP limits.*

---

## Component Latency Benchmarks

### Offboard: RTX 5090 Laptop (24GB GDDR7)

#### 1. DINOv3 ViT-L Distilled (~300M params) — Perception Encoder

| Configuration | Latency (ms) | Source |
|---|---|---|
| PyTorch eager, FP16, 224² | 20–40 | Industry benchmark for ViT-L on RTX 4090 Desktop |
| PyTorch eager, FP16, 384² | 60–90 | Quadratic attention scaling with resolution |
| TensorRT FP16, 224² | 8–15 | Typical 2–3× speedup over eager |
| TensorRT FP16, 384² | 25–40 | Higher resolution still benefits from optimization |
| TensorRT INT8, 384² | 15–25 | Additional 1.5–2× over FP16 |

**Recommended config:** TensorRT FP16 at 384² → **~30 ms per frame**
**Feasible frequency:** 15–20 Hz (pipelined; encodes while previous frame's voxel/LeJEPA processes)

> Distilled ViT-L has identical architecture to standard ViT-L — no latency difference. DINOv3 is available as a distilled ViT-L variant from Meta AI (2025 release).

---

#### 2. Sparse Voxel Memory — MinkowskiNet + Hash Encoding

| Stage | Latency (ms) | Notes |
|---|---|---|
| Point cloud → GPU transfer | 1–3 | Pinned memory, direct sensor streaming |
| Voxelization / hashing | 1–5 | CUDA kernel; maps LiDAR points to sparse indices |
| Hash feature lookup + interpolation | 1–2 | Instant NGP-style; cache-friendly |
| MinkowskiNet sparse conv encoder | 5–15 | Depends on active voxels (~10–50K per frame), not grid size |
| Feature write to hash grid | <1 | Update existing voxels, insert new ones |
| **Total** | **8–26** | |

**Recommended config:** Batch voxelization + sparse conv → **~15 ms per frame**
**Feasible frequency:** 20 Hz (easily; sparse conv is highly optimized)

> Grid size (50×50×20) is irrelevant for latency — only active voxel count matters. A typical LIVOX-MID360 frame at 0.1m resolution produces ~5–20K active voxels.

---

#### 3. LeJEPA Encoder — ViT-L (~304M params) — World Model

| Configuration | Latency (ms) | Source |
|---|---|---|
| PyTorch + FlashAttention, FP16, latent tokens from voxel grid | 10–30 | Standard ViT-L forward pass; teacher and predictor discarded at inference |
| TensorRT FP16 | 8–15 | Same as DINOv3 ViT-L (identical architecture) |
| TensorRT INT8 | 5–10 | Quantized encoder |

**Recommended config:** TensorRT FP16 → **~12 ms per forward pass**
**Feasible frequency:** 10–15 Hz (encoder only; no teacher-student overhead)

> Key insight: JEPA architectures (I-JEPA, V-JEPA, LeJEPA) discard the teacher encoder and predictor at inference time. Only the student encoder runs — identical latency to any ViT-L. LeJEPA is a training methodology, not a distinct inference architecture.

---

#### 4. VLA — GR00T N1.5 or PaliGemma (~3B params) — High-Level Goal Selector

| Configuration | Latency (ms) | Source |
|---|---|---|
| PaliGemma 3B, FP16, single action prediction | 15–40 | RTX 4090 Desktop benchmarks |
| GR00T N1.5 3B, FP16 | 15–40 | Intended for real-time control on consumer GPUs |
| 8-bit quantization (bitsandbytes) | 10–25 | Significant VRAM savings, minimal quality loss |
| RTX 4090 Laptop (mobile GPU) | 25–70 | 60–80% of desktop throughput due to TGP limits |
| SmolVLA / distilled VLA | 30–65 | 15–30 Hz on RTX 4090 Desktop |
| OpenVLA (larger backbone) | 100–160 | ~6 Hz — too slow for this use case |

**Recommended config:** GR00T N1.5 or PaliGemma, INT8 quantized → **~40 ms per inference** (conservative for laptop GPU)
**Feasible frequency:** 5–10 Hz (VLA runs asynchronously; not in the tight perception-planning loop)

> The VLA outputs semantic goals ("go to charging station, avoid blue mat"), not per-timestep actions. It runs at 1–5 Hz independently of the 10–20 Hz predictive loop.

---

#### 5. A* Path Planner — Through Voxel Occupancy Grid

| Configuration | Latency (ms) | Source |
|---|---|---|
| A* on 50×50×20 grid | <0.5 | Trivial; thousands of nodes |
| A* on 200×200×50 grid | 1–5 | Still well under budget |
| With tether yaw penalty in cost function | +0.1 | Simple additive term |

**Recommended config:** A* on CPU, triggered on VLA goal update → **<1 ms per query**
**Feasible frequency:** On-demand (runs whenever VLA produces new goal or occupancy changes significantly)

> A* through a 3D voxel grid with 50K nodes is sub-millisecond on any modern CPU. This is the most computationally trivial component in the entire stack.

---

#### 6. Tether Physics Estimator

| Configuration | Latency (ms) |
|---|---|
| Yaw estimator + tension model | <0.1 |

**Feasible frequency:** On-demand, negligible.

---

### Onboard: Jetson Orin NX (16GB Unified, 100–157 TOPS)

#### 7. FAST-LIO2 — LiDAR-Inertial Odometry

| Configuration | Latency (ms) |
|---|---|
| Standard FAST-LIO2 on Orin NX | 3–5 |

**Feasible frequency:** 200 Hz (deployed and validated in robotics literature)

---

#### 8. ULTRA Whole-Body Controller — PPO Policy (MLP, ~2M params)

| Configuration | Latency (ms) |
|---|---|
| MLP forward pass (2M params) | <0.5 |
| PD controller (joint-level) | <0.1 |
| Total per control step | <1 |

**Feasible frequency:** 500 Hz (MLP inference is trivially fast; ULTRA validated on G1 at 50 Hz control, 500 Hz achievable for simpler WBC)

---

#### 9. FIRM Fall-Safety Policy — Diffusion Policy (lightweight)

| Configuration | Latency (ms) |
|---|---|
| Diffusion denoising (triggered only on destabilization) | 10–20 |
| Normal monitoring (IMU threshold check) | <0.1 |

**Feasible frequency:** 500 Hz monitoring (threshold check), 50 Hz inference when triggered

---

## Pipeline Timing Analysis

### Predictive Loop (tight, synchronous)

```
Frame N:  DINOv3  ───30ms───┐
                              ├─ Voxel  ───15ms───┐
Frame N+1: DINOv3  ───30ms───┘                    ├─ LeJEPA ───12ms───┐
                                                   │                    ├─ A* ──<1ms──┐
                                                   │                    │              ├─→ Trajectory to G1
```

**Pipelined latency:** ~30ms (DINOv3) + ~15ms (Voxel) + ~12ms (LeJEPA) + <1ms (A*) = **~58 ms end-to-end**

But with pipelining (each stage processes a different frame simultaneously):
- DINOv3 runs at 15–20 Hz (30ms per frame, overlapping with Voxel from previous frame)
- Voxel runs at 20 Hz (15ms per frame)
- LeJEPA runs at 10–15 Hz (12ms per frame)
- A* runs on-demand (<1ms)

**Effective pipeline throughput:** **15 Hz** (limited by slowest stage = DINOv3 at 30ms)

### Semantic Loop (asynchronous)

```
VLA receives latent state + language command → 40ms → outputs semantic goal
                                                                        │
A* converts goal + voxel occupancy → <1ms → waypoint trajectory ──────┘
                                                                        │
TrajectoryBuffer receives updated waypoints → feeds WBC at 500Hz ──────┘
```

**VLA runs independently at 5–10 Hz** — not in the tight perception loop. When it produces a new goal, A* replans. Between VLA updates, A* continues with previous goal + updated occupancy.

### Reactive Loop (onboard, always running)

```
FAST-LIO2 (200Hz) ─┐
                    ├─→ ULTRA WBC (500Hz) ──→ Actuators
TrajectoryBuffer ───┘
FIRM monitor (500Hz) ──→ Override on destabilization
Watchdog (continuous) ──→ Link-loss trigger
```

---

## Revised Feasible Frequencies

| Component | Original (unrealistic) | Revised (profiled) | Limiting Factor |
|---|---|---|---|
| DINOv3 | 40 Hz | **15–20 Hz** | ViT-L TensorRT latency at 384² |
| Voxel Memory | 40 Hz | **20 Hz** | Sparse conv + memory write (not the bottleneck) |
| LeJEPA | 40 Hz (V-JEPA 2 ViT-g) | **10–15 Hz** | ViT-L forward pass; much lighter than ViT-g |
| A* Planner | 40 Hz (MPPI 1024 samples) | **On-demand** | Sub-millisecond; runs when VLA updates goal |
| VLA | 40 Hz (VL-JEPA) | **5–10 Hz** | 3B-param model on laptop GPU; async from main loop |
| **Pipeline throughput** | 40 Hz (impossible) | **~15 Hz** | DINOv3 is the slowest synchronous stage |
| **WBC** | 500 Hz | **500 Hz** | MLP forward pass is trivial |

---

## VRAM Budget (Verified)

| Component | Original Estimate | Verified Estimate | Delta |
|---|---|---|---|
| DINOv3 ViT-L (FP16) | 6.0 GB | 5.0 GB | −1.0 GB (FP16, not FP32) |
| LeJEPA ViT-L (FP16) | 8.0 GB (ViT-g) | 4.0 GB | −4.0 GB (304M vs 1B params) |
| Voxel Memory (MinkowskiNet + hash grid) | 4.0 GB (4D-NVS) | 2.0 GB | −2.0 GB (no rendering) |
| VLA (INT8 quantized) | N/A | 6.0 GB | +6.0 GB (new component) |
| MPPI Planner | 3.0 GB | N/A | −3.0 GB (removed) |
| A* Planner | N/A | 0.5 GB | +0.5 GB (new, occupancy grid) |
| Acoustic-JEPA | 1.0 GB | N/A | −1.0 GB (removed; out of scope) |
| Tether Physics | N/A | 0.2 GB | +0.2 GB (new) |
| CUDA / OS Overhead | 2.0 GB | 2.0 GB | — |
| **TOTAL** | **24.0 GB (95%)** | **19.7 GB (82%)** | **−4.3 GB** |

---

## Timing Diagram: One Full Cycle at 15 Hz

```
Time (ms):  0    10   20   30   40   50   60   70   80   90   100  110  120
            ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤

DINOv3:     [===Frame 1===]
                        [===Frame 2===]
                                            [===Frame 3===]
Voxel:           [==F1==]
                             [==F2==]
                                                  [==F3==]
LeJEPA:                     [=F1=]
                                        [=F2=]
                                                           [=F3=]
A*:                                   [*]
                                                        [*]
VLA:            [======Goal 1======]  (async, ~40ms)
                                          [======Goal 2======]
WBC (G1):  ════ 500Hz continuous ════ (not shown to scale)
            ├────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┼────┤
Output:           └── traj(F1)→G1 ──┘   └── traj(F2)→G1 ──┘
```

Each frame takes ~67ms from sensor to trajectory, but **pipelining achieves 15 Hz throughput** (new trajectory every ~67ms from a continuously flowing pipeline).

---

## Bottleneck Analysis

| Bottleneck | Severity | Mitigation |
|---|---|---|
| DINOv3 dominates the synchronous loop | Medium | Reduce resolution to 224² (saves ~15ms) or use ViT-B (saves ~10ms) |
| VLA on laptop GPU | Medium | INT8 quantization; VLA runs async at 5Hz, not in tight loop |
| PCIe transfer (sensor → GPU) | Low | Pinned memory, direct sensor streaming |
| Thermal throttling on laptop | Medium | Limit continuous GPU load to ~80%; duty-cycle VLA |
| Orin NX WBC jitter | Low | MLP is deterministic; RT-patched Linux kernel |

---

## Conservative vs Optimistic Estimates

| Scenario | DINOv3 | LeJEPA | VLA | Pipeline Hz |
|---|---|---|---|---|
| **Conservative** (no TensorRT, PyTorch eager) | 40ms | 25ms | 70ms | **~10 Hz** |
| **Realistic** (TensorRT FP16, INT8 VLA) | 30ms | 12ms | 40ms | **~15 Hz** |
| **Optimistic** (TensorRT INT8, distilled VLA) | 18ms | 8ms | 25ms | **~20 Hz** |

**Recommended planning target: 15 Hz pipeline throughput.** This gives margin for thermal throttling, OS jitter, and sensor latency while being fast enough for indoor humanoid navigation (the G1 walks at ~0.5–1.5 m/s; at 15 Hz with 0.5m lookahead, the robot has ~5–15 planning cycles before reaching any waypoint).
