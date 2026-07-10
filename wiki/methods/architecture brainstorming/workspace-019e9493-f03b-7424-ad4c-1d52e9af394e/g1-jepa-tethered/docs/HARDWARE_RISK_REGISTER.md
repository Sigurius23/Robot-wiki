# Hardware Risk Register: G1 Pipeline Failure Modes & Recovery

> **📋 VRAM numbers:** All VRAM and model size figures in this document reference [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md) (canonical source) and [VRAM_QUICKREF.md](./VRAM_QUICKREF.md) (quick lookup). When in doubt, VRAM_MEASUREMENTS.md is authoritative.

**Date:** June 9, 2026
**References:** [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md), [ARCHITECTURE_VARIATIONS.md](./ARCHITECTURE_VARIATIONS.md) ([Minimum Viable Hardware](./ARCHITECTURE_VARIATIONS.md#minimum-viable-hardware)), [LLM_AND_VLM_ROLES.md](./LLM_AND_VLM_ROLES.md)

---

## 1. Failure Categories

| Category | Description | Detection | Severity |
|:---|:---|:---|:---|
| **VRAM Overflow** | Model weights + KV cache + activations exceed 24 GB GPU memory | `torch.cuda.OutOfMemoryError` | 🔴 Critical — pipeline halts |
| **CPU OOM** | System RAM (64 GB) exhausted by model staging/offloading | `MemoryError`, OOM killer | 🔴 Critical — process killed |
| **GPU Thermal Throttle** | RTX 5090 junction temp exceeds threshold, clocks drop | `nvidia-smi` temp > 85°C | 🟡 Degraded — latency spikes |
| **Tether Link Loss** | Gigabit Ethernet cable disconnected or switch failure | Heartbeat timeout > 50ms | 🔴 Critical — robot isolated |
| **Cosmos 3 API Failure** | vLLM-Omni server crash, NIM container exit, Hugging Face rate limit | HTTP 5xx, connection refused | 🔴 Critical — brain offline |
| **GR00T N1 Inference Fail** | Model crash, NaN output, action out of bounds | Action range check, NaN detection | 🔴 Critical — unsafe actions |
| **Orin NX OOM** | Reactive stack (WBC/CBF) exceeds 16 GB shared memory | Orin kernel OOM | 🔴 Critical — safety layer gone |
| **Cosmos Latency Spike** | Inference takes >30s instead of 10-30s | Wall clock exceeds budget | 🟡 Degraded — stale actions |
| **Disk Full** | 2 TB NVMe fills with model weights + logs | `disk usage > 95%` | 🟡 Degraded — can't download new models |
| **NF4/INT8 Quantization Mismatch** | Using INT8/FP8 instead of NF4 for Cosmos 3 on non-Blackwell GPU — causes VRAM overflow | `torch.cuda.OutOfMemoryError` after model load | 🔴 Critical — pipeline can't start |
| **Jetson AGX Orin Thermal** | Onboard module hits 60W thermal ceiling during sustained Cosmos inference | `tegrastats` junction > 85°C | 🟡 Degraded — throttled, slow cycles |
| **Jetson AGX Orin Latency** | Cosmos 3 inference takes 30–60s on Orin, scene graph becomes stale during action execution | Wall clock > 30s per cycle | 🟡 Degraded — robot acts on outdated scene |

---

## 2. Variation 1: Pure JEPA — Risk Register

### 2.1 VRAM Overflow

> **💡 V-JEPA 2 has 5 model sizes (ViT-B 80M → ViT-G 2B).** Our V1 VRAM numbers assume **ViT-g/16 (1B, ~7.3 GB BF16)** — the community standard for RTX 3090/4090. **V-JEPA 2.1 ViT-G/16 (2B, ~10–12 GB BF16) + MPPI + Voxel = ~15–17 GB BF16** — fits any 24 GB GPU comfortably for best-quality standard JEPA. Smaller variants (ViT-L/16 300M, ~3.5 GB) fit lower-end GPUs. See [VRAM_MEASUREMENTS.md §2](./VRAM_MEASUREMENTS.md#2-v-jepa-2--video-prediction-world-model) and [§2b](./VRAM_MEASUREMENTS.md#2b-v-jepa-21--dense-feature-upgrade).

**Trigger:** Any component exceeds its allocated VRAM budget.

**Two scenarios:**

| Scenario | Components | VRAM (BF16) | VRAM (INT8) | Fits 24 GB? |
|:---|:---|:---|:---|:---|
| **Standard JEPA** (what papers run) | V-JEPA 2 + MPPI + Voxel | ~12.3 GB | ~10.1 GB | ✅ Easily — ~12 GB headroom |
| **Standard JEPA 2B** (V-JEPA 2.1 ViT-G/16) | V-JEPA 2.1 (2B) + MPPI + Voxel | **~15–17 GB** ✅ | ~11–12 GB ✅ | ✅ Fits any 24 GB GPU — best quality |
| **V1 simultaneous** (all 11 components) | DINO + Slot + VL-JEPA + 3DGS + Minkowski + VICReg + NVS4D + V-JEPA 2 + WorldRFT + MPPI + Voxel | ~33.3 GB | ~28.1 GB | ❌ Won't fit |
| **V1 sequential** (standard practice) | Resident (Voxel+MPPI ~5 GB) + max(Semantic ~10.5 GB, Predictive ~19.8 GB) | ~24.8 GB ⚠️ | **~22.6 GB** ✅ | ⚠️ Tight at BF16, ✅ fits at INT8 |
| **V1 seq + optimized** | As above + 10cm MinkowskiNet voxels (saves 4 GB) | ~20.8 GB ✅ | ~18.6 GB ✅ | ✅ Comfortable |

| Failure Mode | Cause | Probability | Impact |
|:---|:---|:---|:---|
| Full load OOM | All models loaded simultaneously | 🔴 **Guaranteed** | Pipeline can't start |
| Predictive loop OOM | V-JEPA 2 + MinkowskiNet + MPPI + Voxel exceed VRAM | 🟡 Medium (during long rollouts) | 40Hz loop freezes |
| Semantic loop OOM | DINO + 3DGS + VL-JEPA + Slot Attention exceed VRAM | 🟢 Low (fewer models) | Scene understanding paused |

**Fallback Strategy: Loop Separation (Model Swapping)**

```
VRAM resident at all times:  4D Voxel Memory (~3 GB) + MPPI (~2 GB)
                                   = ~5 GB baseline

Semantic cycle (every 1-2 seconds):
  Before: Unload Predictive models → Load Semantic models
          1. Unload V-JEPA 2 (~7.3 GB), MinkowskiNet (~6 GB), VICReg (~0.5), NVS4D (~3)
          2. Load DINOv3 (~3 GB), Slot Attention (~0.5), VL-JEPA (~3), 3DGS (~4)
          3. Run Semantic inference (~0.2s)
          4. Unload Semantic models
          5. Reload Predictive models
          Swap latency: ~2-4 seconds per cycle (PCIe 4.0 x16 ~32 GB/s)

Predictive cycle (continuous at 5-40 Hz):
  V-JEPA 2 (~7.3) + MinkowskiNet (~6) + VICReg (~0.5) + NVS4D (~3) + MPPI (~2) + Voxel (~3)
  = ~21.8 GB — FITS while Semantic models unloaded

Total VRAM at any time: ~5 GB (resident) + max(~21.8 GB Predictive, ~10.5 GB Semantic)
                       = ~26.8 GB ❌ STILL DOESN'T FIT

**This swap strategy alone is insufficient.** The resident baseline is too large.
Additional mitigations needed:
• INT8 quantize V-JEPA 2 (7.3 GB → 5.1 GB, saves 2.2 GB)
• Reduce MinkowskiNet voxel resolution 5cm → 10cm (6 GB → ~2 GB, saves 4 GB)
• Combined: ~21.8 GB → ~15.5 GB → total ~20.5 GB ✅ Fits
• OR: Move Voxel Memory to CPU (saves 3 GB GPU, adds <1ms CPU↔GPU latency)
```

**Degraded Operation Mode:** If swapping latency exceeds 2 seconds, drop Semantic loop entirely. Robot operates on last known scene graph + V-JEPA 2 predictions only. Equivalent to "blind predictive" mode.

**Recovery:** On OOM, catch exception → log which model failed → unload non-critical models → retry with reduced batch size / frame count / voxel resolution.

### 2.2 Link Loss

**Existing design covers this** (Link-Loss Buffer, 500ms kinematic decay). See [SYSTEM_INTEGRATION.md](./SYSTEM_INTEGRATION.md).

### 2.3 GPU Thermal Throttle (see also Section 5.2)

**Trigger:** RTX 5090 junction > 85°C during sustained 40Hz MPPI sampling.

**Impact:** GPU clocks drop → MPPI sampling rate drops from 40 Hz → may fall below 5 Hz → trajectory quality degrades.

**Recovery:**
1. Detect: `nvidia-smi -q -d TEMPERATURE` every 5 seconds
2. Mitigate: Reduce MPPI samples from 1024 → 256 (75% VRAM saving, lower quality)
3. If still throttling: Drop from 40 Hz → 10 Hz predictive loop
4. Alert operator: "GPU thermal throttle — reduced planning quality"

---

## 3. Variation 2: Cosmos 3-Centric — Risk Register

### 3.1 VRAM Overflow

**State:** Cosmos 3 NVFP4 Policy mode ~17 GB + Middleware ~3.2 GB = ~20.2 GB / 24 GB. Fits but tight.

| Failure Mode | Cause | Probability | Impact |
|:---|:---|:---|:---|
| Policy mode OOM | KV cache spikes at 720p or long context | 🟡 Medium | Action generation fails |
| Reasoner OOM | Large image input (high-res D435i frame) | 🟢 Low | Scene understanding fails |
| Dual-mode OOM | Reasoner + Generator both loaded with large buffers | 🟡 Medium | Both modes fail |

**Fallback: Graceful Resolution Degradation**

```
Level 1 (Normal):    720p Policy mode, ~19 GB — ⚠️ tight, monitor VRAM
Level 2 (Degraded):  480p Policy mode, ~16 GB — ✅ comfortable, 20% quality loss
Level 3 (Minimal):   Reasoner-only text mode, ~8 GB — ✅ safe, no action generation
                      Robot falls back to last valid action chunk or zero-velocity stand
```

**Recovery Procedure:**
1. Monitor `torch.cuda.memory_allocated()` before each Cosmos call
2. If < 3 GB headroom: downgrade to 480p
3. If < 2 GB headroom: switch to Reasoner-only + reuse last action
4. After resolution downgrade, log warning + notify operator
5. Attempt to restore 720p after 60s cooldown

### 3.2 Cosmos 3 API/Server Failure

**Trigger:** vLLM-Omni server crash, Docker container exit, or NIM microservice failure.

**Impact:** Complete loss of world understanding + action generation. Robot is blind at the Semantic level.

**Fallback: Reasoner-Last-Known-Good (RLKG)**

```
1. Detect: HTTP health check to vLLM-Omni /health endpoint every 2 seconds
2. On failure: 
   a. Log error + timestamp
   b. Robot continues executing last received action chunk (from 4D Voxel Memory)
   c. If action chunk exhausted: zero-velocity stand (link-loss behavior)
3. Recovery attempt: Restart vLLM-Omni server
   docker restart vllm-omni-container
   Wait for "Application startup complete" (~30-90 seconds)
4. If restart fails 3×: Alert operator. Robot enters safe stand.
```

**Recovery Time:** 30-90 seconds for vLLM restart + model reload. During this window, robot operates on buffered actions or stands still.

### 3.3 Cosmos Latency Spike

**Trigger:** Cosmos 3 Policy mode takes >30s (budget is 10-30s). Diffusion denoising gets stuck.

**Recovery:**
1. Detect: Wall clock > 30s since Cosmos request sent
2. Cancel request (HTTP timeout)
3. Retry with 480p + fewer inference steps (35 → 20). Note: 20 steps reduces video quality but is sufficient for action trajectory generation (lower visual fidelity, same action space).
4. If retry also times out: switch to Reasoner-only text goal → reuse last valid action chunk from Voxel Memory
5. Log latency spike for post-mortem

### 3.4 Tether Link Loss

Same as Variation 1 — Link-Loss Buffer triggers zero-velocity stand. **Additional risk:** Cosmos 3 is mid-inference (10-30s call). If link drops during inference, the result is lost. **Mitigation:** Buffer previous successful action chunk. On link return, check if buffered action is still valid (voxel memory hasn't detected new obstacles).

---

## 4. Variation 4: Cosmos 3 + GR00T N1 — Risk Register (Deep Dive)

### 4.1 VRAM Overflow — The Dual-Model Problem

**State:** Cosmos Reasoner ~8 GB + GR00T N1 ~7 GB + Middleware ~3 GB = ~18 GB. **Fits with Reasoner-only.** But Cosmos Policy (~17 GB) + GR00T (~7 GB) = ~24 GB without middleware, ~27 GB with middleware. **Does NOT fit.**

| Scenario | VRAM | Fits? | Fallback |
|:---|:---|:---|:---|
| Cosmos Reasoner + GR00T + Middleware | ~18 GB | ⚠️ Fits | — |
| Cosmos Policy (480p) + GR00T + Middleware | ~26 GB | ❌ OOM | Sequential swap (see 4.2) |
| Cosmos Policy (720p) + GR00T + Middleware | ~29 GB | ❌ OOM | Sequential swap |
| Cosmos Reasoner + GR00T both loaded + spike | ~18→22 GB | ⚠️ Triggered | Resolution degrade |

### 4.2 Sequential Execution Strategy (The Primary Fallback)

When Cosmos Policy mode is needed, run sequentially — only one large model in VRAM at a time:

```
Phase 1: Cosmos World Understanding (10-30 seconds)
  ┌─────────────────────────────────────────────┐
  │ VRAM State:                                  │
  │  Cosmos 3 Policy (NVFP4): ~17 GB            │
  │  4D Voxel Memory:         ~3 GB             │
  │  Action Adapter:          ~0.1 GB           │
  │  TOTAL:                   ~20.1 GB ✅        │
  │                                              │
  │  GR00T N1: UNLOADED (on CPU or disk)        │
  │                                              │
  │  Action: Cosmos generates goals + scene     │
  └─────────────────────────────────────────────┘
                │
                │ Cosmos output stored in CPU RAM
                ▼
         ┌─────────────┐
         │ MODEL SWAP   │  Unload Cosmos Generator from GPU
         │              │  Load GR00T N1 to GPU
         │ Latency:     │
         │  2-4s (GPU→CPU transfer)            │
         └──────┬──────┘
                │
                ▼
Phase 2: GR00T Action Generation (20-40 Hz)
  ┌─────────────────────────────────────────────┐
  │ VRAM State:                                  │
  │  GR00T N1:                ~7 GB             │
  │  4D Voxel Memory:         ~3 GB             │
  │  Action Adapter:          ~0.1 GB           │
  │  TOTAL:                   ~10.1 GB ✅        │
  │                                              │
  │  Cosmos 3 Generator: UNLOADED               │
  │  Cosmos 3 Reasoner:     ~8 GB (KEPT!)       │
  │                                              │
  │  Action: GR00T generates action chunks      │
  └─────────────────────────────────────────────┘
```

**Key insight:** Keep Cosmos Reasoner (~8 GB) resident at all times. Only swap the Generator (~9 GB additional) and GR00T N1 (~7 GB).

**Resident VRAM budget:** Reasoner (8) + Voxel (3) + Adapter (0.1) = ~11.1 GB.  
**Swappable budget:** Generator add-on (9) OR GR00T N1 (7).  
**Peak VRAM with swap:** 11.1 + max(9, 7) = ~20.1 GB. ✅

### 4.3 CPU Offloading Strategy (Alternative to Swapping)

Instead of full GPU unload/reload, keep model weights in CPU RAM and swap layers on-demand:

```
GPU VRAM (24 GB):
  Resident:   Cosmos Reasoner (8 GB)
              Voxel Memory (3 GB)
              Adapter (0.1 GB)
              ─────────────────
              ~11.1 GB baseline

  Active:     Cosmos Generator layers (streamed from CPU)
         OR   GR00T N1 layers (streamed from CPU)

CPU RAM (64 GB):
  Staged:     Cosmos Generator full weights: ~17 GB (NVFP4 weights ~8 GB + buffers)
              GR00T N1 full weights: ~7 GB
              ─────────────────
              ~24 GB staged on CPU
              ~40 GB remaining for OS + datasets
```

**Offloading latency:** PCIe 4.0 x16 = ~32 GB/s theoretical. Per-layer transfer: ~0.5-2 GB = ~15-60 ms per layer. For 40-layer model: ~1-2 seconds to swap full model. **Faster than full unload/reload** but adds per-layer latency during inference.

### 4.4 Combined Fallback Hierarchy (Variation 4)

```
Level 0 (Nominal):     Cosmos Reasoner resident + GR00T N1 in GPU
                       Simple tasks: GR00T handles directly
                       VRAM: ~18 GB ⚠️

Level 1 (CPU Offload): Cosmos Generator layers streamed from CPU RAM
                       No full model swap — per-layer PCIe transfer
                       Slower inference per layer but no 2-4s pause
                       VRAM: ~20 GB
                       Latency cost: +15–60ms per layer (amortized in forward pass)

Level 2 (Full Swap):   Cosmos Policy loaded → GR00T unloaded → GPU
                       Cosmos runs Policy → output stored in CPU RAM
                       Swap → GR00T loaded → actions generated
                       VRAM: ~20 GB during Cosmos, ~18 GB during GR00T
                       Latency cost: +2–4s total swap pause
                       Use when CPU offload is too slow for task requirements

Level 3 (Reasoner-Only): Cosmos Generator unloaded, GR00T loaded
                       Cosmos Reasoner provides text goals only (no video prediction)
                       GR00T N1 generates actions from text goals
                       VRAM: ~18 GB
                       Quality loss: no physics-grounded video verification

Level 4 (GR00T-Only):   Cosmos fully unloaded
                       GR00T N1 operates from last scene graph in Voxel Memory
                       VRAM: ~10 GB
                       Quality loss: no Cosmos scene understanding

Level 5 (Safe Stand):   Both Cosmos and GR00T unloaded
                       Voxel Memory + WBC only
                       Robot executes zero-velocity stand
                       VRAM: ~3 GB
```

### 4.5 GR00T N1 NaN/Action Safety

**Trigger:** GR00T N1 outputs NaN or action values outside [-1, 1] normalized range.

**Detection:**
```python
if np.any(np.isnan(action)) or np.any(np.abs(action) > 1.5):
    raise ActionSafetyError(f"Invalid GR00T action: range [{action.min()}, {action.max()}]")
```

**Fallback:**
1. Discard current action chunk
2. Reuse last valid action chunk (from Voxel Memory buffer)
3. If 3 consecutive invalid outputs: escalate to Level 5 (Safe Stand)
4. Log full GR00T input (camera frame + Cosmos goal) for debugging

### 4.6 HPC Training Pipeline Failure

**Trigger:** HPC cluster unavailable (maintenance, queue timeout, job failure).

**Impact:** Can't fine-tune Cosmos/GR00T. Inference continues on RTX 5090 with current weights. **Not a runtime failure** — only affects model improvement cadence.

**Fallback:** Train locally on RTX 5090 with smaller batch sizes (overnight). Accept longer training times but maintain pipeline operation.

---

### 4.7 CPU OOM During Model Staging

**Trigger:** 64 GB system RAM exhausted by staging model weights for CPU offloading.

**Detection:** `psutil.virtual_memory().percent > 90%` or `MemoryError` on allocation.

**Fallback:**
1. Evict lowest-priority staged model from CPU RAM (GR00T N1 ~7 GB first, since it's lighter to reload)
2. If still OOM: evict Cosmos Generator from CPU (~17 GB), accept that Policy mode requires full GPU swap
3. If still OOM: kill non-essential processes (logging daemon, monitoring scripts)
4. Alert operator: "CPU OOM — reduced to Reasoner-only mode"

**Prevention:** Maintain >20 GB free CPU RAM at all times. Staged model weights are read-only (can be reloaded from NVMe in ~2-5 seconds if evicted).

---

## 5. Cross-Cutting Risks (All Variations)

### 5.0 Unverified VRAM Estimates

The following component VRAM numbers are **legacy estimates not yet verified** in [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md):
- VICReg: ~0.5 GB (estimated — minor, unlikely to be significantly different)
- 4D Neural Voxel Splatting: ~3 GB (estimated — could be 2-5 GB depending on splat density)
- 3D Gaussian Splatting: ~4 GB (estimated — depends on scene complexity)
- GR00T N1: ~7 GB (estimated — no public VRAM benchmarks available; could be 5-10 GB depending on precision and deployment format)

**Risk:** Actual VRAM could be ±50% from estimates, changing feasibility verdicts.
**Mitigation:** Benchmark these components on RTX 5090 before deployment. Flag any estimate >20% off in the risk register.

### 5.1 Tether Link Loss — Universal Fallback

All variations share this risk. The Link-Loss Buffer is already designed:

```
Detection: Heartbeat message from RTX 5090 every 10ms.
           If no heartbeat for >50ms → link loss declared.

Immediate: TrajectoryBuffer on Orin NX activates.
           Continues executing last 500ms of valid trajectory.
           Robot performs controlled deceleration to zero velocity.

Recovery:  On link restoration (<5s): resume from current state.
           On prolonged outage (>5s): robot enters safe stand.
           Operator notified via audio/visual alert.

VRAM note: Link loss does not affect RTX 5090 VRAM.
           Models remain loaded, waiting for reconnection.
```

### 5.2 GPU Thermal Emergency

**Trigger:** Any variation running sustained inference. RTX 5090 at 40W "Super Mode" for >60 minutes.

**Detection:** `nvidia-smi -q -d TEMPERATURE` → junction > 88°C.

**Fallback (ordered):**
1. Reduce inference frequency (halve the loop rate)
2. Reduce MPPI samples or Cosmos resolution
3. Enable GPU fan curve override (aggressive cooling)
4. If temp > 92°C: emergency pause all GPU inference → robot safe stand
5. Resume when temp < 80°C

### 5.3 Orin NX OOM

**Trigger:** Reactive stack exceeds 16 GB shared memory. Rare but possible with large voxel grid + IMU buffer overflow.

**Fallback:**
1. Sparse Voxel Memory evicts oldest/least-certain voxels (LRU with uncertainty weight)
2. Reduce voxel resolution from 5cm → 10cm (halves active voxel count)
3. If still OOM: drop Voxel Memory entirely, rely on FAST-LIO2 + CBF only
4. Robot operates without blind-spot awareness (degraded but safe)

### 5.4 Disk Full

**Trigger:** 2 TB NVMe fills with Cosmos model weights (~32 GB download) + logs + cached data.

**Prevention:** Monitor disk usage. Maintain >100 GB free.
**Fallback:** Purge oldest model checkpoints. Compress logs. Reduce logging verbosity.

### 5.5 NF4/INT8 Quantization Mismatch — Cosmos 3 on Non-Blackwell GPUs

**Trigger:** Loading Cosmos 3 on a non-Blackwell GPU (RTX 3090/4090, Jetson AGX Orin) using INT8 or FP8 quantization instead of 4-bit NF4.

**Why this is dangerous:** The minimum VRAM numbers for V2/V4/V12 assume **4-bit quantization** (~17 GB Policy, ~8 GB Reasoner). But:
- **NVFP4** (Blackwell) = hardware-accelerated 4-bit. Only on RTX 5090.
- **NF4** (Bitsandbytes) = software 4-bit. Works on all GPUs, matching VRAM footprint.
- **FP8** = 8-bit. Cosmos Policy ~23 GB + middleware ~3 GB = **~26 GB — OOM on 24 GB.**
- **INT8** = 8-bit. Cosmos Policy ~25 GB + middleware ~3 GB = **~28 GB — OOM on 24 GB, let alone 16 GB.**

If a developer loads Cosmos 3 with `load_in_8bit=True` (the default in many inference scripts) instead of `load_in_4bit=True` on an RTX 3090, the pipeline OOMs immediately.

| GPU | Correct Quantization | VRAM (Policy) | Wrong Quantization | VRAM (Policy) | Result |
|:---|:---|:---|:---|:---|:---|
| RTX 5090 (Blackwell) | NVFP4 | ~17 GB ✅ | FP8 | ~23 GB ⚠️ tight | — |
| RTX 4090 (Ada) | NF4 (Bitsandbytes) | ~17 GB ✅ | FP8 | ~23 GB ❌ OOM | INT8 | ~25 GB ❌ OOM |
| RTX 3090 (Ampere) | NF4 (Bitsandbytes) | ~17 GB ✅ | INT8 | ~25 GB ❌ OOM | FP8 | N/A (not supported) |
| RTX 4060 Ti 16GB (Ada) | NF4 | ~17 GB ❌ still OOM | — | — | 16 GB insufficient for any Policy mode |
| Jetson AGX Orin (Ampere) | INT4 (TensorRT) | ~14 GB ⚠️ | INT8 | ~25 GB 🐌 Unnecessary — use INT4 | FP8 | N/A (not supported) |

**Detection:**
```python
# During model loading, check quantization config
if model_config.quantization in ("int8", "fp8") and gpu_vram < 32_GB:
    raise QuantizationRiskError(
        f"Cosmos 3 with {model_config.quantization} requires >24 GB VRAM. "
        f"Use NF4 (bitsandbytes) or NVFP4 (Blackwell only) instead."
    )
```

**Fallback:**
1. Catch OOM during model load → log quantization config that caused it
2. Retry with `load_in_4bit=True` (NF4 via Bitsandbytes) or NVFP4 checkpoint
3. If NF4 also OOMs on 16 GB card: fall back to Reasoner-only mode (~8 GB NF4)
4. On Jetson AGX Orin: use TensorRT-LLM INT4 build, not Hugging Face INT8

**Prevention:** Enforce quantization config validation before model load. The VRAM monitor (checklist item 1) should include a quantization check for Cosmos 3 models.

### 5.6 Jetson AGX Orin — Edge Deployment Risks

**Context:** The Jetson AGX Orin 64GB is our primary candidate for untethered operation. It runs Cosmos 3 (verified by NVIDIA via JetPack) but with significant constraints. See [ARCHITECTURE_VARIATIONS.md §Untethered Viability](./ARCHITECTURE_VARIATIONS.md#untethered-viability-analysis).

#### 5.6.1 Thermal Throttle at 60W

**Trigger:** Sustained Cosmos 3 inference pushes the Orin module to its 60W power ceiling. Unlike the actively-cooled RTX 5090, the Orin inside the G1 has limited airflow.

**Detection:** `tegrastats` or `jetson_clocks --show` → GPU frequency drops below max, junction temp > 85°C.

**Impact:** Inference time spikes from 30s → 90s+ per Cosmos call as clocks throttle. Scene queries become unusably stale.

**Fallback:**
1. Detect thermal throttle via `tegrastats` every 5 seconds
2. Cap Orin power mode at 40W (reduces peak TOPS but prevents throttle cycling)
3. Increase Cosmos call interval from 10s → 30s minimum (allows cooling between calls)
4. If junction > 90°C: pause all inference, robot enters safe stand, wait for temp < 75°C
5. Alert operator: "Orin thermal — extended safe stand"

**Prevention:** Run Orin at 30–40W sustained (not 60W MAXN). Accept slower inference for thermal stability. Add active cooling fan to the G1's compute bay if possible.

#### 5.6.2 Stale Scene Graph from 30–60s Cosmos Latency

**Trigger:** Cosmos 3 takes 30–60 seconds per full call on Jetson AGX Orin (275 TOPS INT8 vs RTX 5090's Blackwell throughput). During this window, the robot is executing actions based on a scene that is 30–60 seconds old.

**Why this is dangerous:** The G1 can walk ~15–30 meters in 30 seconds. Obstacles, people, or objects that appeared after the last Cosmos call are invisible to the planner.

**Scenario:**
```
t=0s:  Cosmos sees clear path → GR00T generates 50-timestep walk trajectory
t=5s:  Person walks into path
t=15s: G1 continues walking (following t=0 trajectory)
t=25s: CBF detects imminent collision → emergency stop
t=35s: Cosmos finally returns ("person detected in path") — already stopped
```

**Fallback (ordered by severity):**
1. **Voxel Memory as freshness buffer:** The 4D Voxel Memory runs on the Orin NX at 10–20 Hz, updating occupancy from FAST-LIO2 in real-time. Even though Cosmos is slow, the voxel grid reflects live LiDAR data. If new obstacles appear in the planned path, the CBF safety filter (500 Hz, always running) triggers avoidance. In V1 (which includes MPPI), MPPI can also replan around detected obstacles. In V2/V4 (no MPPI), CBF is the sole avoidance mechanism — this is sufficient for reactive safety but won't generate optimized alternative trajectories.
2. **Split the loop:** Don't run Cosmos on Orin. Run Cosmos on RTX 5090 (tethered) for scene understanding, and only run GR00T N1 on Orin for action generation. This keeps the action loop at 10–40 Hz while accepting slower scene updates from the tether.
3. **Reactive override:** CBF safety filter runs at 500 Hz on Orin NX regardless of Cosmos state. If collision is imminent, CBF overrides the planned trajectory and executes avoidance.
4. **Safe stand on stale timeout:** If Cosmos hasn't returned within 60s, robot enters zero-velocity stand until fresh scene data arrives.
5. **Distilled fallback (V7):** Keep a lightweight distilled student policy (~200M params) on Orin NX. When Cosmos on AGX Orin is too slow, switch to the distilled policy for basic obstacle avoidance.

**Prevention:**
- Always pair slow Cosmos (Orin) with a fast reactive layer (CBF + Voxel Memory on Orin NX).
- Set maximum scene age: if Cosmos result is >45s old, discard and use Voxel Memory + last valid GR00T actions.
- For untethered deployment, prefer V7 (Distilled) for real-time control + Cosmos for occasional scene re-evaluation.

---

## 6. Recovery Time Summary

| Failure | Detection | Recovery Action | Recovery Time | Robot Behavior During |
|:---|:---|:---|:---|:---|
| VRAM OOM (V1) | Instant (exception) | Model swap or degrade | 2-4s | Stand still (last valid trajectory) |
| VRAM OOM (V2) | Instant | Resolution degrade | <1s | Brief pause, resume at 480p |
| VRAM OOM (V4, dual) | Instant | Sequential swap | 2-4s | Stand still during Cosmos→GR00T swap |
| Cosmos server crash | Health check (2s interval) | Docker restart | 30-90s | Execute buffered actions then stand |
| GR00T NaN output | Per-inference check | Reuse last valid | <1ms | No visible pause |
| Link loss (tether) | Heartbeat (10ms) | TrajectoryBuffer | <50ms | Smooth deceleration to stop |
| GPU thermal >88°C | nvidia-smi (5s) | Reduce load / fan | 10-30s | Reduced quality, no stop needed |
| GPU thermal >92°C | nvidia-smi (5s) | Emergency pause | 60-120s | Safe stand until cooled |
| Orin NX OOM | Instant (OOM killer) | Voxel eviction | <1s | Momentary pause, loss of blind-spot awareness |
| Disk full | Monitor (60s) | Purge old data | <30s | No impact on operation |
| NF4/INT8 mismatch | On model load (instant) | Retry with NF4 or fallback to Reasoner-only | <10s | Pipeline restart with correct quantization |
| Jetson Orin thermal | tegrastats (5s) | Cap at 40W, increase cooldown | 10–30s | Slower but stable Cosmos cycles |
| Jetson Orin stale scene | Wall clock age check | CBF + Voxel Memory live override | <50ms (CBF) | Safe avoidance, no full stop needed |

---

## 7. Risk Matrix (Probability × Impact)

| Risk | Probability | Impact | Score | Mitigation Priority |
|:---|:---|:---|:---|:---|
| V1 VRAM OOM (simultaneous) | 🔴 High (guaranteed if loaded at once) | 🔴 High | **Critical** | Implement sequential execution — standard practice, fits at INT8. 2B variant (V-JEPA 2.1) fits standard JEPA at BF16 (~15–17 GB) ✅ |
| V2 VRAM OOM (720p) | 🟡 Medium | 🟡 Medium | **Medium** | Resolution auto-degrade |
| V4 dual-model OOM | 🟡 Medium | 🔴 High | **High** | Sequential swap mandatory |
| Cosmos server crash | 🟡 Medium | 🔴 High | **High** | Auto-restart + buffered actions |
| Link loss | 🟢 Low | 🔴 High | **Medium** | Already designed |
| GPU thermal | 🟡 Medium (sustained 40Hz) | 🟡 Medium | **Medium** | Monitor + throttle |
| GR00T NaN | 🟢 Low | 🔴 High | **Medium** | Per-inference check |
| Orin NX OOM | 🟢 Low | 🔴 High | **Medium** | Voxel eviction |
| Disk full | 🟢 Low | 🟡 Low | **Low** | Disk monitor |
| Cosmos latency spike | 🟡 Medium | 🟡 Low | **Low** | Timeout + retry |
| NF4/INT8 mismatch | 🟡 Medium | 🔴 High | **High** | Enforce quantization config validation |
| Jetson Orin thermal | 🟡 Medium (sustained Cosmos) | 🟡 Medium | **Medium** | Cap at 40W, increase cooldown |
| Jetson Orin stale scene | 🔴 High (30-60s Cosmos call) | 🔴 High | **Critical** | CBF + Voxel Memory + V7 fallback |

---

## 8. Jetson Thor — Future Hardware Risk Mitigation

**What it is:** NVIDIA's next-generation edge AI module. Blackwell architecture, 128 GB unified LPDDR5X memory, ~2,070 FP4 TOPS, NVFP4 native. 40–130W power envelope. Announced but not yet released (June 2026).

**Which risks Thor eliminates:**

| Current Risk | Thor Mitigation | Details |
|:---|:---|:---|
| **VRAM overflow (all variations)** | 128 GB unified memory — fits V1 (33 GB), V4 full (27 GB), V13 (32 GB) simultaneously | No model swapping needed. All models co-resident. |
| **NVFP4/NF4 quantization mismatch** | NVFP4 native via Blackwell tensor cores | No Bitsandbytes workaround. Hardware-accelerated 4-bit at full speed. |
| **Jetson AGX Orin thermal throttle** | 2,070 TOPS at up to 130W with better perf/W than Ampere | Cosmos inference in seconds, not minutes. Thermal headroom for sustained operation. |
| **Stale scene graph (30–60s Cosmos)** | RTX 5090-class transformer throughput at the edge | Cosmos returns in 1-10s (RTX 5090-class) instead of 30-60s on Jetson AGX Orin. Scene graph stays fresh. |
| **Tether dependency (V2, V4, V10)** | Full untethered Cosmos + GR00T simultaneously | No tether needed. Robot operates autonomously with desktop-class AI. |
| **CPU OOM during model staging** | 128 GB unified — no CPU/GPU split | No staging, no offloading. Everything in unified memory. |
| **Multi-model co-residency (V4, V12-V14)** | 128 GB fits Cosmos Policy + GR00T + Gemma 4 + Voxel + WBC | All models loaded simultaneously. No sequential swap. |

**What risks Thor does NOT eliminate:**
- **Power budget:** 40–130W is higher than Orin (15–60W). Battery life impact on the G1 must be evaluated.
- **Physical integration:** Thor is a different form factor than Orin NX. May require a new carrier board or mounting.
- **Software maturity:** New Blackwell edge platform — JetPack/Isaac ROS support may lag behind Ampere.
- **Cost:** TBA, but likely $3,000–$5,000 for the module.

**When Thor becomes available, the risk register simplifies dramatically:**
- Variations 1, 2, 4, 5, 10, 12, 13, 14 all become viable untethered.
- The only remaining deployment risk is battery life (power budget).
- Model swapping, CPU offloading, and quantization gymnastics become unnecessary.
- The tether becomes strictly optional — used only for HPC training data transfer.

**Migration path when Thor ships:**
1. Flash JetPack (Blackwell) onto Thor module
2. Deploy Cosmos 3 Nano NVFP4 + GR00T N1 + 4D Voxel Memory → all on Thor
3. Re-purpose Orin NX as dedicated CBF/WBC safety co-processor (500 Hz, 4 GB). **Note:** Thor (40–130W) + Orin NX (10–15W) + 43 motors may challenge the G1's battery budget. Evaluate total power draw before committing to a two-module architecture. Alternative: run CBF/WBC directly on Thor (it has plenty of compute headroom), keeping only one module.
4. Remove tether — robot is fully autonomous
5. RTX 5090 repurposed as training GPU or second-robot inference server

---

## 9. Implementation Checklist

- [ ] **VRAM monitor**: `torch.cuda.memory_allocated()` before every model load
- [ ] **Resolution auto-degrade**: VRAM headroom < 3 GB → switch 720p → 480p
- [ ] **Sequential loop execution (V1):** Semantic loop → unload → Predictive loop. Standard JEPA practice — NOT a workaround. Fits at INT8 (~22.6 GB). See [VRAM_MEASUREMENTS.md §6](./VRAM_MEASUREMENTS.md#6-corrected-vram-budgets-per-variation).
- [ ] **No simultaneous V1 load:** Never load all 11 V1 components at once (~33 GB — guaranteed OOM). Only one loop's models in VRAM at any time.
- [ ] **Model swap orchestration** (V4): Cosmos Policy ↔ GR00T N1 swap
- [ ] **vLLM-Omni health check**: HTTP GET /health every 2s, auto-restart on failure
- [ ] **GR00T NaN guard**: Validate action range before sending to WBC
- [ ] **Action buffer**: Store last 3 valid action chunks in Voxel Memory
- [ ] **GPU temp monitor**: `nvidia-smi` polling at 5s intervals
- [ ] **Orin OOM handler**: LRU voxel eviction on memory pressure
- [ ] **Disk monitor**: Warn at 90%, block model downloads at 95%
- [ ] **Quantization config validator**: Enforce NF4 for Cosmos 3 on non-Blackwell GPUs. Block INT8/FP8 loads that would OOM. See §5.5.
- [ ] **Orin power mode cap**: Set Jetson AGX Orin to 30–40W MAXN_CUSTOM (not 60W) for thermal stability. See §5.6.1.
- [ ] **Scene age monitor**: Track wall-clock age of Cosmos result. Discard if >45s old. Use Voxel Memory + CBF as live fallback. See §5.6.2.
- [ ] **Thor readiness checklist**: When Thor ships — JetPack flash, NVFP4 deployment, Orin NX reassignment as safety co-processor. See §8.
- [ ] **Operator alerts**: Audio cue for degraded mode, visual indicator for safe stand
