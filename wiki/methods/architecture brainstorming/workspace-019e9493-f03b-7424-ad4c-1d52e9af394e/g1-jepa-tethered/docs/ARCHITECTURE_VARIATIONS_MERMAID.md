# G1 Pipeline Architecture Variations — Mermaid.js Diagrams

> **📋 VRAM numbers:** All VRAM and model size figures in this document reference [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md) (canonical source) and [VRAM_QUICKREF.md](./VRAM_QUICKREF.md) (quick lookup). When in doubt, VRAM_MEASUREMENTS.md is authoritative.

**Date:** June 9, 2026
**Renders in:** GitHub, Obsidian, VS Code (with Mermaid plugin), any Markdown viewer with Mermaid support.

These are the three most important variations from [ARCHITECTURE_VARIATIONS.md](./ARCHITECTURE_VARIATIONS.md), converted to Mermaid flowchart syntax **with hardware feasibility annotations** (VRAM, latency, memory budget, network).

---

## Hardware Reference

| Resource | Capacity | Constraint |
|:---|:---|:---|
| **RTX 5090 VRAM** | 24 GB | All offboard models must fit here |
| **RTX 5090 RAM** | 64 GB | CPU offloading fallback, model weight staging |
| **RTX 5090 Storage** | 2 TB NVMe | Cosmos3-Nano weights ~32 GB download |
| **Orin NX RAM** | 16 GB | Shared CPU/GPU memory; ~4 GB for reactive stack |
| **Orin NX Compute** | 100 TOPS | INT8 inference only; no FP16/BF16 large models |
| **Gigabit Ethernet** | ~125 MB/s | <1 ms latency; camera frames + action targets |
| **HPC Cluster** | Multi-GPU | Batch only; no real-time; for training/SDG |

### Hardware Feasibility Key

| Symbol | Meaning |
|:---|:---|
| ✅ | Fits comfortably |
| ⚠️ | Tight — requires quantization/offloading |
| ❌ | Doesn't fit on this hardware |
| 🔷 | HPC only (batch, no real-time) |

---

## Variation 1: Pure JEPA — The Baseline

```mermaid
graph TD
    subgraph RTX5090["🖥️ RTX 5090 — 24 GB VRAM / 64 GB RAM"]
        subgraph Semantic["SEMANTIC LOOP — 0.5–1 Hz"]
            DINO["DINOv3 (ViT-g/14, 1.1B)<br/>⚠️ ~3 GB BF16<br/>1.5 GB INT8"] --> Slot["Slot Attention<br/>~0.5 GB"]
            Slot --> VLJEPA["VL-JEPA<br/>~3 GB"]
            GS3D["3DGS Lab Twin<br/>⚠️ ~4 GB"] --> Slot
        end

        Semantic -->|"object slots + text goals"| Predictive

        subgraph Predictive["4D PREDICTIVE LOOP — 5–40 Hz"]
            Mink["MinkowskiNet (4D, 5cm)<br/>⚠️ ~6 GB<br/>Sparse, 10-25× vs dense"] --> VICReg["VICReg<br/>~0.5 GB"]
            VICReg --> NVS4D["4D Neural Voxel Splat<br/>⚠️ ~3 GB"]
            NVS4D --> VJEPA2["V-JEPA 2 (ViT-g, 16fr)<br/>⚠️ ~7.3 GB BF16<br/>5.1 GB INT8"]
            VJEPA2 --> WorldRFT["WorldRFT<br/>~1 GB"]
            WorldRFT --> MPPI["Tether-Aware MPPI<br/>1024 samples<br/>~2 GB"]
            MPPI --> VoxelMem["4D Voxel Memory<br/>~3 GB<br/>• Rearward blind spots<br/>• Uncertainty damping"]
            VoxelMem --> MPPI
        end

        Budget["VRAM BUDGET (sequential, ViT-g/16 1B):<br/>Standard JEPA: ~12 GB BF16 ✅<br/>Std JEPA 2B (V-JEPA 2.1 ViT-G/16): ~15–17 GB BF16 ✅<br/>V1 simultaneous: ~33 GB ❌ (worst case)<br/>V1 sequential INT8: ~22.6 GB / 24 GB ✅<br/>V1 seq + 10cm voxels: ~18.6 GB ✅<br/>5 model sizes: ViT-B→ViT-G (see VRAM_MEAS §2, §2b)<br/>REF: docs/VRAM_MEASUREMENTS.md §2, §2b, §6"]
    end

    Predictive -->|"43D joints @ 40 Hz<br/>GigE <1ms latency"| Orin

    subgraph Orin["🤖 Jetson Orin NX — 16 GB Shared / 100 TOPS"]
        subgraph Reactive["REACTIVE LOOP — 500 Hz"]
            FASTLIO["FAST-LIO2<br/>✅ ~1 GB"] --> CBF["CBF Safety Filter<br/>✅ ~0.5 GB"]
            CBF --> LinkLoss["Link-Loss Buffer<br/>500ms decay<br/>✅ ~0.1 GB"]
            LinkLoss --> WBC["Whole-Body Controller<br/>IK/ID QP solver<br/>✅ ~2 GB<br/>→ 43 DoF EtherCAT"]
        end

        Sensors["Sensors<br/>MID-360 LiDAR · D435i · IMU · Encoder<br/>✅ ~0.5 GB streaming"] --> FASTLIO
        OrinBudget["ORIN BUDGET: ~4 GB / 16 GB ✅ Fits"]
    end

    style RTX5090 fill:#1a1a2e,stroke:#e94560,color:#eee
    style Orin fill:#0f3460,stroke:#00b4d8,color:#eee
    style Semantic fill:#16213e,stroke:#e94560,color:#eee
    style Predictive fill:#16213e,stroke:#e94560,color:#eee
    style Reactive fill:#0a1628,stroke:#00b4d8,color:#eee
    style Budget fill:#332211,stroke:#ffaa00,color:#ffaa00
    style OrinBudget fill:#112233,stroke:#00b4d8,color:#00b4d8
    style VoxelMem fill:#533483,stroke:#c77dff,color:#eee
    style WBC fill:#03506f,stroke:#00b4d8,color:#eee
    style DINO fill:#e9456020,stroke:#e94560,color:#eee
    style Slot fill:#e9456020,stroke:#e94560,color:#eee
    style VLJEPA fill:#e9456020,stroke:#e94560,color:#eee
    style Mink fill:#e9456020,stroke:#e94560,color:#eee
    style VICReg fill:#e9456020,stroke:#e94560,color:#eee
    style NVS4D fill:#e9456020,stroke:#e94560,color:#eee
    style VJEPA2 fill:#e9456020,stroke:#e94560,color:#eee
    style WorldRFT fill:#e9456020,stroke:#e94560,color:#eee
    style MPPI fill:#e9456020,stroke:#e94560,color:#eee
    style FASTLIO fill:#00b4d820,stroke:#00b4d8,color:#eee
    style CBF fill:#00b4d820,stroke:#00b4d8,color:#eee
    style LinkLoss fill:#00b4d820,stroke:#00b4d8,color:#eee
    style GS3D fill:#e9456020,stroke:#e94560,color:#eee
    style Sensors fill:#0f3460,stroke:#00b4d8,color:#888
```

**Hardware verdict:** ⚠️ **Fits with sequential execution** (~22.6 GB INT8 / ~24.8 GB BF16). The diagram shows ALL components simultaneously (~33 GB BF16) — this is the worst case. **Standard JEPA** (V-JEPA 2 + MPPI + Voxel = ~12 GB) fits easily on any 24 GB GPU, consistent with published papers. **Standard JEPA with V-JEPA 2.1 ViT-G/16 (2B)**: ~15–17 GB BF16 — best quality, fits any 24 GB GPU comfortably. **Our V1 with sequential loops** (Semantic → unload → Predictive, standard robotics practice) fits at INT8 comfortably. With 10cm MinkowskiNet voxels: ~18.6 GB INT8 ✅. See [VRAM_MEASUREMENTS.md §6](./VRAM_MEASUREMENTS.md#6-corrected-vram-budgets-per-variation) and [§2b](./VRAM_MEASUREMENTS.md#2b-v-jepa-21--dense-feature-upgrade). ✅ Orin NX comfortable (~4 GB / 16 GB).

---

## Variation 2: Cosmos 3-Centric

```mermaid
graph TD
    subgraph RTX5090["🖥️ RTX 5090 — 24 GB VRAM / 64 GB RAM"]
        subgraph Cosmos3["COSMOS 3 NANO — 16B params"]
            Reasoner["REASONER Tower (8B)<br/>Autoregressive VLM<br/>• Scene caption<br/>• Object grounding<br/>• Task planning"]
            Generator["GENERATOR Tower (8B)<br/>Diffusion Transformer<br/>• Text→Video (SDG)<br/>• Forward Dynamics<br/>• Policy: 29D actions"]

            Quant["QUANTIZATION CHOICE:"]
            BF16["BF16: ~32 GB weights + overhead ❌"]
            FP8["FP8: ~23 GB total ⚠️ Very tight"]
            NVFP4["NVFP4: ~16-17 GB total<br/>8 GB weights + 8-9 GB KV/buffers<br/>⚠️ Fits, little headroom<br/>REF: VRAM_MEASUREMENTS.md"]

            Quant --> BF16
            Quant --> FP8
            Quant --> NVFP4

            Reasoner <-->|"Joint Attention"| Generator
        end

        Reasoner -->|"text goals<br/>+ scene graph"| Adapter
        Generator -->|"video + 29D action<br/>chunk × 50 timesteps"| Adapter

        subgraph MidLayer["MIDDLEWARE — 10–40 Hz"]
            Adapter["Action Adapter<br/>✅ ~0.1 GB<br/>• 29D→43D remap<br/>• Denormalize + clamp<br/>• Tether yaw penalty"] --> VoxelMem["4D Voxel Memory<br/>✅ ~3 GB<br/>• Persists Cosmos outputs<br/>• Rearward blind spots<br/>• Uncertainty damping"]
            VoxelMem --> Interp["Trajectory Interpolator<br/>✅ ~0.1 GB<br/>• Chunk → 40Hz stream"]
        end

        Budget["VRAM BUDGET (NVFP4, Policy mode):<br/>Cosmos 3: ~17 GB + Middleware: ~3.2 GB<br/>Total ~20.2 GB / 24 GB ⚠️ TIGHT<br/>Reasoner-only mode: ~11.2 GB ✅<br/>REF: VRAM_MEASUREMENTS.md<br/>Latency: Reasoner 1–3s, Policy 10–30s"]
    end

    Interp -->|"43D joints @ 40 Hz<br/>GigE <1ms"| Orin

    subgraph Orin["🤖 Jetson Orin NX — 16 GB / 100 TOPS"]
        subgraph Reactive["REACTIVE LOOP — 500 Hz"]
            WBC["WBC + CBF + Link-Loss Buffer<br/>✅ ~4 GB<br/>• IK/ID · Safety · 500ms decay<br/>• 43 DoF → EtherCAT"]
        end
        Sensors["Sensors → WBC<br/>✅ ~0.5 GB"]
        Sensors -.->|"camera frames via Ethernet<br/>~3 MB/frame @ 30fps = 90 MB/s"| Cosmos3
    end

    style RTX5090 fill:#1a1a2e,stroke:#e94560,color:#eee
    style Orin fill:#0f3460,stroke:#00b4d8,color:#eee
    style Cosmos3 fill:#0d1b2a,stroke:#00ff88,color:#eee
    style Reasoner fill:#00ff8820,stroke:#00ff88,color:#00ff88
    style Generator fill:#00ff8820,stroke:#00ff88,color:#00ff88
    style Quant fill:#0d1b2a,stroke:#ffaa00,color:#ffaa00
    style BF16 fill:#ff000030,stroke:#ff0000,color:#ff6666
    style FP8 fill:#ffaa0030,stroke:#ffaa00,color:#ffaa00
    style NVFP4 fill:#00ff8830,stroke:#00ff88,color:#00ff88
    style MidLayer fill:#16213e,stroke:#e94560,color:#eee
    style Reactive fill:#0a1628,stroke:#00b4d8,color:#eee
    style Budget fill:#112211,stroke:#00ff88,color:#00ff88
    style Adapter fill:#e9456020,stroke:#e94560,color:#eee
    style VoxelMem fill:#533483,stroke:#c77dff,color:#eee
    style Interp fill:#e9456020,stroke:#e94560,color:#eee
    style WBC fill:#03506f,stroke:#00b4d8,color:#eee
    style Sensors fill:#0f3460,stroke:#00b4d8,color:#888
```

**Hardware verdict:** ⚠️ **Tight but fits** (~20 GB / 24 GB in Policy mode). Our previous ~8/11 GB estimate was too optimistic — only counted weight VRAM, missed KV cache and CUDA buffers (~8 GB additional). Reasoner-only mode is lighter at ~11 GB. ❌ BF16 won't fit. FP8 is borderline (~23 GB). NVFP4 is mandatory. See [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md). ✅ Orin NX comfortable. ⚠️ Camera stream @ 90 MB/s under GigE's 125 MB/s ceiling.

---

## Variation 4: Cosmos 3 + GR00T N1 Hybrid

```mermaid
graph TD
    subgraph HPC["☁️ HPC Cluster — Batch Only, No Real-Time"]
        CosmosSuper["Cosmos 3 Super (64B)<br/>🔷 H100/B200 required<br/>• Synthetic Data Generation<br/>• GR00T-Dreams trajectories<br/>• Batch fine-tuning"]
        IsaacSim["Isaac Sim + Isaac Lab<br/>🔷 Multi-GPU training<br/>• Physics-accurate G1 sim<br/>• Domain randomization<br/>• RL/IL training"]
        CosmosSuper -->|"synthetic data"| IsaacSim
        IsaacSim -.->|"fine-tuned weights<br/>(offline transfer)"| RTX5090
    end

    subgraph RTX5090["🖥️ RTX 5090 — 24 GB VRAM / 64 GB RAM"]
        subgraph Cosmos3["COSMOS 3 NANO — 0.1–0.5 Hz"]
            CosmosReason["REASONER<br/>'What's in the scene?'<br/>⚠️ ~8 GB (NVFP4 reasoner-only)"]
            CosmosGen["GENERATOR<br/>Video prediction<br/>⚠️ ~17 GB (NVFP4 full model)"]
            CosmosReason <--> CosmosGen
        end

        Cosmos3 -->|"text goals + task-space<br/>waypoints + predicted video"| GROOT

        subgraph GROOT["GR00T N1 — 20–40 Hz"]
            Sys2["SYSTEM 2 (Slow)<br/>Goal → Sub-tasks<br/>⚠️ Est. ~4 GB"] --> Sys1["SYSTEM 1 (Fast)<br/>29D action chunks<br/>⚠️ Est. ~3 GB"]
        end

        Sys1 -->|"29D action chunks"| MidLayer

        subgraph MidLayer["MIDDLEWARE"]
            Adapter["Action Adapter<br/>✅ ~0.1 GB"] --> VoxelMem["4D Voxel Memory<br/>✅ ~3 GB"]
        end

        VRAMPressure["⚠️ VRAM PRESSURE (NVFP4):<br/>Cosmos reasoner-only: ~8 GB + GR00T N1: ~7 GB<br/>+ Middleware: ~3 GB = ~18 GB / 24 GB ⚠️<br/>Cosmos full model + GR00T = ~27 GB ❌<br/>Must run Cosmos reasoner-only OR swap<br/>REF: VRAM_MEASUREMENTS.md"]
        NetworkPressure["⚠️ NETWORK: Cosmos → GR00T → Adapter<br/>Internal GPU transfer (no network cost)<br/>RTX→Orin: 43D @ 40Hz ≪ GigE"]
    end

    MidLayer -->|"43D joints @ 40 Hz<br/>GigE <1ms"| Orin

    subgraph Orin["🤖 Jetson Orin NX — 16 GB / 100 TOPS"]
        subgraph Reactive["REACTIVE LOOP — 500 Hz"]
            WBC["WBC + CBF + Link-Loss<br/>✅ ~4 GB / 16 GB"]
        end
        Sensors["Sensors → WBC<br/>✅ ~0.5 GB"]
        Sensors -.->|"camera frames<br/>~90 MB/s"| Cosmos3
    end

    style HPC fill:#1b0a2e,stroke:#c77dff,color:#eee
    style RTX5090 fill:#1a1a2e,stroke:#e94560,color:#eee
    style Orin fill:#0f3460,stroke:#00b4d8,color:#eee
    style Cosmos3 fill:#0d1b2a,stroke:#00ff88,color:#eee
    style CosmosReason fill:#00ff8820,stroke:#00ff88,color:#00ff88
    style CosmosGen fill:#00ff8820,stroke:#00ff88,color:#00ff88
    style GROOT fill:#0d1b2a,stroke:#ff6b35,color:#eee
    style Sys1 fill:#ff6b3520,stroke:#ff6b35,color:#ff6b35
    style Sys2 fill:#ff6b3520,stroke:#ff6b35,color:#ff6b35
    style MidLayer fill:#16213e,stroke:#e94560,color:#eee
    style Reactive fill:#0a1628,stroke:#00b4d8,color:#eee
    style VRAMPressure fill:#332211,stroke:#ffaa00,color:#ffaa00
    style NetworkPressure fill:#112233,stroke:#00b4d8,color:#00b4d8
    style CosmosSuper fill:#c77dff20,stroke:#c77dff,color:#c77dff
    style IsaacSim fill:#c77dff20,stroke:#c77dff,color:#c77dff
    style Adapter fill:#e9456020,stroke:#e94560,color:#eee
    style VoxelMem fill:#533483,stroke:#c77dff,color:#eee
    style WBC fill:#03506f,stroke:#00b4d8,color:#eee
    style Sensors fill:#0f3460,stroke:#00b4d8,color:#888
```

**Hardware verdict:** ⚠️ **Fits only with Cosmos Reasoner-only** (~18 GB). Full Cosmos + GR00T = ~27 GB ❌. Sequential execution required: keep Cosmos Reasoner resident (~8 GB), swap Generator in/out for world queries. Or: run Cosmos → unload → GR00T → unload → Cosmos. 🔷 HPC required for training. See [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md).

---

## Hardware Feasibility Comparison

```mermaid
graph LR
    subgraph V1["V1: Pure JEPA"]
        V1vram["Standard JEPA: ~12 GB BF16 ✅<br/>Std JEPA 2B: ~15-17 GB BF16 ✅<br/>V1 seq INT8: ~22.6 GB ⚠️<br/>V1 simultaneous: ~33 GB ❌"]
        V1lat["Latency: 40 Hz ✅"]
        V1feas["✅ Standard JEPA fits easily<br/>⚠️ V1 fits with sequential<br/>❌ V1 doesn't fit simultaneously"]
    end

    subgraph V2["V2: Cosmos-Centric"]
        V2vram["VRAM: ~20 GB ⚠️ (Policy)<br/>~11 GB ✅ (Reasoner)"]
        V2lat["Latency: 0.1–1 Hz ⚠️"]
        V2feas["⚠️ Fits (Policy)<br/>✅ Comfortable (Reasoner)"]
    end

    subgraph V4["V4: Cosmos + GR00T"]
        V4vram["VRAM: ~27 GB ❌ (Full Cosmos)<br/>~18 GB ⚠️ (Reasoner-only)"]
        V4lat["Latency: 20-40 Hz ✅"]
        V4feas["❌ Full / ⚠️ Reasoner-only"]
    end

    style V1 fill:#16213e,stroke:#e94560,color:#eee
    style V2 fill:#0d1b2a,stroke:#00ff88,color:#eee
    style V4 fill:#0d1b2a,stroke:#ff6b35,color:#eee
    style V1vram fill:#ff000020,stroke:#ff0000,color:#ff6666
    style V1lat fill:#112211,stroke:#00ff88,color:#00ff88
    style V1feas fill:#ff000020,stroke:#ff0000,color:#ff6666
    style V2vram fill:#332211,stroke:#ffaa00,color:#ffaa00
    style V2lat fill:#332211,stroke:#ffaa00,color:#ffaa00
    style V2feas fill:#332211,stroke:#ffaa00,color:#ffaa00
    style V4vram fill:#ff000020,stroke:#ff0000,color:#ff6666
    style V4lat fill:#112211,stroke:#00ff88,color:#00ff88
    style V4feas fill:#332211,stroke:#ffaa00,color:#ffaa00
```

---

## Detailed Hardware Budget Per Variation

| Resource | V1: Pure JEPA | V2: Cosmos-Centric | V4: Cosmos + GR00T |
|:---|:---|:---|:---|
| **RTX 5090 VRAM** | Std JEPA ~12 GB ✅ / Std JEPA 2B ~15-17 GB ✅ / V1 seq ~22.6 GB ⚠️ / V1 sim ~33 GB ❌ | ~20 GB ⚠️ (Policy) / ~11 GB ✅ (Reasoner) | ~18 GB ⚠️ (Reasoner) / ~27 GB ❌ (Full) |
| **RTX 5090 RAM** | ~10 GB for datasets | ~8 GB for model staging | ~12 GB for model staging |
| **RTX 5090 Storage** | ~5 GB model weights | ~32 GB Cosmos3-Nano download | ~40 GB both models |
| **Orin NX RAM** | ~4 GB / 16 GB ✅ | ~4.5 GB / 16 GB ✅ | ~4.5 GB / 16 GB ✅ |
| **Orin NX Compute** | ~20 TOPS (CBF+WBC) | ~20 TOPS (CBF+WBC) | ~20 TOPS (CBF+WBC) |
| **GigE Bandwidth** | ~5 MB/s (43D@40Hz) | ~5 MB/s + ~90 MB/s camera | ~5 MB/s + ~90 MB/s camera |
| **HPC Required?** | No ✅ | No ✅ | Yes 🔷 (training only) |
| **Quantization Required?** | No (custom models) | Yes — NVFP4 essential | Yes — NVFP4 essential |
| **GPU Sharing?** | All custom, shared | Single model | Two models ⚠️ |

## Network Budget

| Stream | Direction | Bandwidth | Latency Budget |
|:---|:---|:---|:---|
| Camera frames (D435i 720p@30fps) | Orin → RTX 5090 | ~90 MB/s | <5 ms |
| Action targets (43D float32 @ 40Hz) | RTX 5090 → Orin | ~7 KB/s (negligible) | <1 ms required |
| Gigabit Ethernet ceiling | Bidirectional | ~125 MB/s | — |
| **Total camera + actions** | — | ~90 MB/s | ✅ Under ceiling |

## Key Hardware Insights

1. **VRAM is the binding constraint.** The RTX 5090's 24 GB is the ceiling. NVFP4 quantization is mandatory for Cosmos 3. See [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md).
2. **Variation 2 (Cosmos-Centric) Reasoner-only is best fit** at ~11 GB — fast scene Q&A without video generation.
3. **Variation 2 Policy mode** uses ~20 GB — fits but very tight.
4. **Variation 1 (Pure JEPA) fits with sequential execution.** Standard JEPA = ~12 GB BF16 ✅, standard JEPA with V-JEPA 2.1 2B = ~15–17 GB BF16 ✅, V1 kitchen sink sequential INT8 = ~22.6 GB ✅. Only V1 simultaneous load (~33 GB) doesn't fit — and no one does that.
5. **Variation 4 only works with Cosmos Reasoner-only** (~18 GB). Full Cosmos + GR00T = ~27 GB ❌.
5. **Orin NX is never the bottleneck** — all variations use ~4 GB / 16 GB for the reactive stack.
6. **Gigabit Ethernet is not a bottleneck** — camera stream (~90 MB/s) + actions (negligible) fit under 125 MB/s.
7. **HPC is only needed for training** (Variation 4 and optionally Variation 8/10). Real-time inference stays on the RTX 5090.

## Color Legend

| Color | Meaning |
|:---|:---|
| 🟢 Green border | NVIDIA Foundation Models (Cosmos 3, GR00T N1) |
| 🔴 Red/Pink | Our custom components (MPPI, Adapter, Interpolator) |
| 🟣 Purple | 4D Voxel Latent Memory (our unique differentiator) |
| 🔵 Cyan | Onboard reactive safety (WBC, CBF, FAST-LIO2) |
| 🟡 Yellow text | Hardware budget warnings |
| ✅ Green check | Fits comfortably |
| ⚠️ Yellow warning | Tight — needs optimization |
| ❌ Red X | Doesn't fit |
| 🔷 Purple diamond | HPC only (batch, offline) |

## Rendering Tips

- **GitHub**: These render natively in any `.md` file — just view the file on GitHub.
- **Obsidian**: Works out of the box. Use ````mermaid` code blocks.
- **VS Code**: Install the "Markdown Preview Mermaid Support" extension.
- **Dark mode**: The diagrams use dark theme colors. For light mode viewers, the text will still be readable (white on colored backgrounds).

## See Also

- **[ARCHITECTURE_VARIATIONS.md](./ARCHITECTURE_VARIATIONS.md)** — All 10 variations, migration pathways, decision guide, and **[Minimum Viable Hardware](./ARCHITECTURE_VARIATIONS.md#minimum-viable-hardware)** section (cheapest GPU per variation, untethered analysis, Jetson Thor upgrade path)
- **[VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md)** — Real inference VRAM footprints for all models
- **[HARDWARE_RISK_REGISTER.md](./HARDWARE_RISK_REGISTER.md)** — Failure modes and recovery strategies per variation
