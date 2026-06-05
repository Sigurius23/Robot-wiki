# G1-JEPA-World-Model: Feasibility Review

*Added 2025-06-05 based on review of README, ROADMAP, SYSTEM_INTEGRATION, HARDWARE_RESOURCES, TRANSITION_PLAN, VALIDATION_PLAN, and source stubs.*

## Architecture Overview

The design proposes a **tethered humanoid architecture**: the Unitree G1 runs onboard proprioceptive control (FAST-LIO2, WBC, CBF @ 500Hz on Orin NX) while an offboard RTX 5090 laptop handles semantic perception, world modeling, and planning (DINOv3, V-JEPA 2, MPPI, 4D-NVS @ 40Hz over Gigabit Ethernet).

---

## Component-by-Component Assessment

| Component | Feasibility | Rationale |
|---|---|---|
| **DINOv3 for segmentation** | ✅ Plausible | ViT-L distilled running at 40Hz on RTX 5090 is achievable with TensorRT. Well-grounded in literature. |
| **Slot Attention for object binding** | ⚠️ Stretch | Slot Attention is typically slow (iterative attention). Real-time at 40Hz on complex scenes is unproven. Alternatives like SAM 2 or DEVA may be more practical. |
| **V-JEPA 2 as world model** | ⚠️ Stretch | ViT-g predictor is ~1B params. A single forward pass takes ~5-10ms even optimized. The architecture needs this for MPPI rollouts — that's the bottleneck. |
| **MPPI with 1024 samples @ 40Hz** | ❌ Infeasible | 1024 samples × 15-step horizon = 15,360 V-JEPA forward passes per planning step. At 40Hz (25ms budget), this would require each forward pass in ~1.6µs. Even batched on an RTX 5090, this is ~100-1000× beyond current hardware. Realistic: ~16-64 samples at 5-10Hz. |
| **4D Neural Voxel Splatting** | ❌ Misdirected | 4D-NVS is a novel-view rendering technique, not designed for real-time robotics. The VRAM budget allocates 4GB to this while the MPPI/V-JEPA pipeline is starved. This is the wrong tool for dynamic scene representation — a simple temporal voxel grid would suffice. |
| **Energy-Based Constraints (EBC)** | ✅ Sound concept | Cosine similarity pruning in latent space is elegant and computationally cheap. The theory is solid — the bottleneck is the JEPA predictions it depends on. |
| **Sparse Voxel Memory** | ✅ Feasible | MinkowskiNet sparse convolutions + hash-based voxel storage is well-established. 50×50×20 grid at 0.1m resolution is modest. |
| **CBF @ 500Hz on Orin NX** | ✅ Solid | Proprioceptive-only CBFs at 500Hz are well within Orin NX capabilities. This is the most grounded component. |
| **HJI Reachability in latent space** | ❌ Research-grade | Computing backward reachable sets for a learned latent dynamics model is an open problem. No published method does this reliably. Treat as aspirational. |
| **Tethered mechanical system** | ⚠️ High-risk | Gigabit slip ring + active tension spool on a walking humanoid adds significant mechanical complexity. Cable entanglement during 360° turns, trip hazards during backward walking, and tension control during rapid gait transitions are unsolved problems at this scale. |
| **TrajectoryBuffer link-loss safety** | ✅ Well-designed | The 500ms kinematic decay buffer is the best piece of engineering in the design. Simple, testable, and directly addresses the tether's primary failure mode. |

---

## Critical Bottlenecks

### 1. Compute — the V-JEPA + MPPI pipeline
The entire architecture hinges on running V-JEPA 2 predictions inside an MPPI loop at 40Hz. The math doesn't close: even with TensorRT INT8 quantization, a ViT-g forward pass on an RTX 5090 takes ~3-5ms. With 1024 samples × 15 horizon steps, you'd need ~46-77 *seconds* per planning step, not 25ms. **Reduce to 16 samples × 5-step horizon at 5Hz for a realistic target.**

### 2. 4D-NVS is the wrong abstraction
You don't need photorealistic novel-view synthesis for a world model that only the planner consumes. Replace with a simple temporal voxel grid with learned feature decay — saves ~4GB VRAM and eliminates a GPU-heavy renderer.

### 3. HJI in latent space is aspirational
Replace with a simpler uncertainty-thresholded fallback: when epistemic uncertainty (from the voxel memory's age) exceeds a threshold, trigger conservative behavior. This is implementable today.

### 4. Tether mechanics are under-specified
The slip ring + spool design needs a physical prototype before assuming it works on a walking humanoid. Consider starting with an untethered "shadow mode" deployment first (as the validation plan already suggests).

---

## What's Well-Designed

- **The three-tier frequency decomposition** (0.5-1Hz semantic, 5-40Hz predictive, 500Hz reactive) is architecturally sound and follows best practices from legged robotics
- **The TrajectoryBuffer** is genuinely clever and implementable
- **The validation plan** (digital twin → HIL → shadow mode) is rigorous and appropriate
- **The literature mapping** correctly identifies relevant papers for each component
- **Rearward navigation via voxel memory queries** is a smart solution to the G1's 59° vertical LiDAR blind spot
- **The semantic s_nogo EBC formulation** is elegant and computationally tractable

---

## Bottom Line

| Dimension | Rating |
|---|---|
| **Vision & research direction** | ⭐⭐⭐⭐⭐ Excellent |
| **Component selection (literature)** | ⭐⭐⭐⭐ Strong |
| **Compute budget realism** | ⭐⭐ Over-optimistic by ~100× |
| **Implementation depth** | ⭐ Skeleton stubs only |
| **Deployability (6 months)** | ❌ Not feasible |
| **Deployability (2-3 years)** | ⚠️ Possible with scope reduction |

**This is an excellent research roadmap, not an implementation plan.** The right next step is to descope aggressively: drop 4D-NVS, reduce MPPI to 16-64 samples at 5-10Hz, replace HJI with uncertainty-thresholded fallback, and get a minimal perception→planning→safety loop running in simulation first.
