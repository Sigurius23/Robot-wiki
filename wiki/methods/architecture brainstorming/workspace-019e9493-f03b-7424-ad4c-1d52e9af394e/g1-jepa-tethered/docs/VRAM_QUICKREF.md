# VRAM Quick Reference Card

> **🔢** This is a generated summary of canonical numbers from [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md). That file is the authoritative source — **update numbers there, then regenerate this card.** Do NOT edit numbers directly in this file; always update VRAM_MEASUREMENTS.md first.

**Date:** June 9, 2026

---

## Model Inference VRAM (Quick Lookup)

| Component | BF16 | INT8 / NF4 | Notes |
|:---|:---|:---|:---|
| DINOv3 (ViT-g/14) | ~3.0 GB | ~1.5 GB | Pure vision encoder, single forward pass |
| V-JEPA 2 ViT-g/16 (1B, 16fr) | ~7.3 GB | ~5.1 GB | Community standard for 24 GB GPUs |
| V-JEPA 2.1 ViT-G/16 (2B, 16fr) | ~10–12 GB | ~6–7 GB | Fits 24 GB comfortably |
| MinkowskiNet (4D, 5cm) | ~6.0 GB | — | Activation-driven, not weight-driven |
| MinkowskiNet (4D, 10cm) | ~2.0 GB | — | Reduced voxel resolution |
| Cosmos 3 Nano Policy (NVFP4) | ~17 GB | — | Blackwell NVFP4 native |
| Cosmos 3 Nano Reasoner (NVFP4) | ~8 GB | — | Text-only, no video generation |
| GR00T N1 | ~7 GB | — | Estimated, no public benchmarks |
| 4D Voxel Memory | ~3 GB | — | Our own code |
| WBC + CBF + FAST-LIO2 | ~4 GB | — | Onboard Orin NX, measured |

---

## V-JEPA 2 Model Variants

| Variant | Params | BF16 (16fr) | INT8 (16fr) | Fits |
|:---|:---|:---|:---|:---|
| ViT-B/16 | 80 M | ~1.5 GB | ~0.8 GB | 8 GB ✅ |
| ViT-L/16 | 300 M | ~3.5 GB | ~2.0 GB | 12 GB ✅ |
| ViT-H/16 | 600 M | ~6.0 GB | ~3.5 GB | 16 GB ✅ |
| **ViT-g/16** ⭐ | **1.0 B** | **~7.3 GB** | **~5.1 GB** | 24 GB — community standard |
| ViT-G/16 (2.1) | 2.0 B | ~10–12 GB | ~6–7 GB | 24 GB ✅ |

---

## Per-Variation VRAM Budget (On RTX 5090 24 GB)

| Variation | Standard JEPA | With 2B Variant | Kitchen Sink (seq) | Fits? |
|:---|:---|:---|:---|:---|
| **V1** Pure JEPA | ~12 GB BF16 ✅ | ~15–17 GB BF16 ✅ | ~22.6 GB INT8 ⚠️ | ✅ Sequential |
| **V2** Cosmos-Centric | — | — | ~20 GB NVFP4 ⚠️ | ✅ Policy mode |
| **V4** Cosmos+GR00T | — | — | ~18 GB Reasoner ⚠️ | ⚠️ Reasoner-only |
| **V7** Minimal Onboard | — | — | ~4–8 GB on Orin NX ✅ | ✅ Untethered |

---

## GPU Tier List

| GPU | VRAM | NVFP4? | Cheapest For… | Price |
|:---|:---|:---|:---|:---|
| RTX 3060 12GB | 12 GB | ❌ | Standard JEPA, V3, V9 | ~$250 |
| RTX 4060 Ti 16GB | 16 GB | ❌ | Cosmos Reasoner-only | ~$500 |
| RTX 3090 (used) | 24 GB | ❌ | V1 seq, V2 Policy (NF4) | ~$700 |
| RTX 5090 | 24 GB | ✅ | **We own this** — best fit | Owned |
| Jetson AGX Orin | 64 GB | ❌ | Untethered (slow, INT4) | ~$2,000 |
| Jetson Thor | 128 GB | ✅ | Untethered dream (TBA) | TBA |

---

## Key Numbers To Remember

- **Standard JEPA** (V-JEPA 2 + MPPI + Voxel) = **~12 GB BF16** — fits any 24 GB GPU
- **Standard JEPA 2B** (V-JEPA 2.1 ViT-G/16 + MPPI + Voxel) = **~15–17 GB BF16** — fits 24 GB
- **Cosmos Policy barrier:** 16 GB GPUs can't run it (~17 GB minimum)
- **NVFP4 is Blackwell-only** — other GPUs must use NF4 (BitSandbytes) for Cosmos
- **V1 kitchen sink simultaneous:** ~33 GB ❌ — but no one does that. Sequential execution fits.
- **Canonical source:** [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md)

---

## See Also

- [VRAM_MEASUREMENTS.md](./VRAM_MEASUREMENTS.md) — Full research, methodology, and per-component breakdown
- [ARCHITECTURE_VARIATIONS.md](./ARCHITECTURE_VARIATIONS.md) — All 10+ variations with MVH per variation
- [HARDWARE_RISK_REGISTER.md](./HARDWARE_RISK_REGISTER.md) — Failure modes and recovery strategies
