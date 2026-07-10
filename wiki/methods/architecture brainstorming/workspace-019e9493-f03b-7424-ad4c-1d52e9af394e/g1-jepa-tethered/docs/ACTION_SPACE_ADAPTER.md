# G1 Action Space Adapter: Cosmos 3 (29D AgiBot) → G1 (43D)

**Date:** June 9, 2026
**Purpose:** Map Cosmos 3's 29-dimensional AgiBot humanoid action space to the Unitree G1's 43 degrees of freedom.

---

## 1. The Two Action Spaces

### Cosmos 3 AgiBot 29D Action Space

Cosmos 3 outputs actions via its Generator tower in Policy or Inverse Dynamics mode. The `agibot_humanoid` domain produces a **29-dimensional vector** of absolute joint angle targets, normalized to `[-1, 1]`, which map to joint limits on the AgiBot hardware.

| Body Part | DoF | Joints |
|:---|:---|:---|
| Left Leg | 6 | Hip Yaw, Hip Roll, Hip Pitch, Knee Pitch, Ankle Pitch, Ankle Roll |
| Right Leg | 6 | Hip Yaw, Hip Roll, Hip Pitch, Knee Pitch, Ankle Pitch, Ankle Roll |
| Waist/Torso | 3 | Waist Yaw, Waist Roll, Waist Pitch |
| Left Arm | 7 | Shoulder Pitch, Shoulder Roll, Shoulder Yaw, Elbow Pitch, Wrist Roll, Wrist Pitch, Wrist Yaw |
| Right Arm | 7 | Shoulder Pitch, Shoulder Roll, Shoulder Yaw, Elbow Pitch, Wrist Roll, Wrist Pitch, Wrist Yaw |
| **Total** | **29** | |

### Unitree G1 43-DoF Configuration

Our G1 (EDU Edition with Dex3-1 hands) has 43 total degrees of freedom. The body uses 29 DoF — functionally identical in topology to the AgiBot layout — plus 14 DoF from the dexterous hands.

**29-DoF Body (from isri-aist/g1_description URDF):**

| Index | G1 Joint Name | Axis | Body Part |
|:------|:---|:---|:---|
| 0 | left_hip_pitch_joint | +Y | Left Leg |
| 1 | left_hip_roll_joint | +X | Left Leg |
| 2 | left_hip_yaw_joint | +Z | Left Leg |
| 3 | left_knee_joint | +Y | Left Leg |
| 4 | left_ankle_pitch_joint | +Y | Left Leg |
| 5 | left_ankle_roll_joint | +X | Left Leg |
| 6 | right_hip_pitch_joint | +Y | Right Leg |
| 7 | right_hip_roll_joint | +X | Right Leg |
| 8 | right_hip_yaw_joint | +Z | Right Leg |
| 9 | right_knee_joint | +Y | Right Leg |
| 10 | right_ankle_pitch_joint | +Y | Right Leg |
| 11 | right_ankle_roll_joint | +X | Right Leg |
| 12 | waist_yaw_joint | +Z | Torso |
| 13 | waist_roll_joint | +X | Torso |
| 14 | waist_pitch_joint | +Y | Torso |
| 15 | left_shoulder_pitch_joint | +Y | Left Arm |
| 16 | left_shoulder_roll_joint | +X | Left Arm |
| 17 | left_shoulder_yaw_joint | +Z | Left Arm |
| 18 | left_elbow_joint | +Y | Left Arm |
| 19 | left_wrist_roll_joint | +X | Left Arm |
| 20 | left_wrist_pitch_joint | +Y | Left Arm |
| 21 | left_wrist_yaw_joint | +Z | Left Arm |
| 22 | right_shoulder_pitch_joint | +Y | Right Arm |
| 23 | right_shoulder_roll_joint | +X | Right Arm |
| 24 | right_shoulder_yaw_joint | +Z | Right Arm |
| 25 | right_elbow_joint | +Y | Right Arm |
| 26 | right_wrist_roll_joint | +X | Right Arm |
| 27 | right_wrist_pitch_joint | +Y | Right Arm |
| 28 | right_wrist_yaw_joint | +Z | Right Arm |

**14-DoF Hands (Dex3-1, 7 per hand):**

| Index | G1 Joint Name | Finger |
|:------|:---|:---|
| 29 | left_hand_thumb_1 | L Thumb |
| 30 | left_hand_thumb_2 | L Thumb |
| 31 | left_hand_thumb_3 | L Thumb |
| 32 | left_hand_index_1 | L Index |
| 33 | left_hand_index_2 | L Index |
| 34 | left_hand_middle_1 | L Middle |
| 35 | left_hand_middle_2 | L Middle |
| 36 | right_hand_thumb_1 | R Thumb |
| 37 | right_hand_thumb_2 | R Thumb |
| 38 | right_hand_thumb_3 | R Thumb |
| 39 | right_hand_index_1 | R Index |
| 40 | right_hand_index_2 | R Index |
| 41 | right_hand_middle_1 | R Middle |
| 42 | right_hand_middle_2 | R Middle |

---

## 2. Key Insight: Same Topology

**Both the AgiBot 29-DoF and the G1 29-DoF body have identical kinematic topology:**

- 6-DoF legs (hip yaw/roll/pitch, knee pitch, ankle pitch/roll)
- 3-DoF waist (yaw, roll, pitch)
- 7-DoF arms (shoulder pitch/roll/yaw, elbow pitch, wrist roll/pitch/yaw)

This means the adaptation problem is primarily a **joint ordering remapping** with some **range scaling**, NOT a structural retargeting problem. The hands (14 DoF) are the only genuinely new degrees of freedom.

---

## 3. Adaptation Strategies

### Strategy A: Functional Joint Remapping (Recommended — Phase 1)

**How it works:** Map each Cosmos 3 output dimension to the functionally equivalent G1 joint, then pad with neutral hand positions.

```
Cosmos 3 29D output:
  [l_hip_yaw, l_hip_roll, l_hip_pitch, l_knee, l_ankle_pitch, l_ankle_roll,   ← Left leg (6)
   r_hip_yaw, r_hip_roll, r_hip_pitch, r_knee, r_ankle_pitch, r_ankle_roll,   ← Right leg (6)
   waist_yaw, waist_roll, waist_pitch,                                          ← Waist (3)
   l_shoulder_pitch, l_shoulder_roll, l_shoulder_yaw, l_elbow, l_wrist_roll, l_wrist_pitch, l_wrist_yaw,  ← Left arm (7)
   r_shoulder_pitch, r_shoulder_roll, r_shoulder_yaw, r_elbow, r_wrist_roll, r_wrist_pitch, r_wrist_yaw]  ← Right arm (7)

        ↓ Joint Mapping Table (permutation + scaling) ↓

G1 43D output:
  [l_hip_pitch, l_hip_roll, l_hip_yaw, l_knee, l_ankle_pitch, l_ankle_roll,   ← Left leg (6)
   r_hip_pitch, r_hip_roll, r_hip_yaw, r_knee, r_ankle_pitch, r_ankle_roll,   ← Right leg (6)
   waist_yaw, waist_roll, waist_pitch,                                          ← Waist (3)
   l_shoulder_pitch, l_shoulder_roll, l_shoulder_yaw, l_elbow, l_wrist_roll, l_wrist_pitch, l_wrist_yaw,  ← Left arm (7)
   r_shoulder_pitch, r_shoulder_roll, r_shoulder_yaw, r_elbow, r_wrist_roll, r_wrist_pitch, r_wrist_yaw,  ← Right arm (7)
   l_thumb_1, l_thumb_2, l_thumb_3, l_index_1, l_index_2, l_middle_1, l_middle_2,  ← Left hand (7, neutral)
   r_thumb_1, r_thumb_2, r_thumb_3, r_index_1, r_index_2, r_middle_1, r_middle_2]  ← Right hand (7, neutral)
```

**Joint Mapping Table:**

| Cosmos 3 Index | AgiBot Joint (assumed) | → | G1 Index | G1 Joint | Scale/Note |
|:---|:---|---:|:---|:---|:---|
| 0 | L Hip Yaw | → | 2 | left_hip_yaw_joint | Reorder (0→2) |
| 1 | L Hip Roll | → | 1 | left_hip_roll_joint | Reorder (1→1) |
| 2 | L Hip Pitch | → | 0 | left_hip_pitch_joint | Reorder (2→0) |
| 3 | L Knee | → | 3 | left_knee_joint | Direct |
| 4 | L Ankle Pitch | → | 4 | left_ankle_pitch_joint | Direct |
| 5 | L Ankle Roll | → | 5 | left_ankle_roll_joint | Direct |
| 6 | R Hip Yaw | → | 8 | right_hip_yaw_joint | Reorder |
| 7 | R Hip Roll | → | 7 | right_hip_roll_joint | Reorder |
| 8 | R Hip Pitch | → | 6 | right_hip_pitch_joint | Reorder |
| 9 | R Knee | → | 9 | right_knee_joint | Direct |
| 10 | R Ankle Pitch | → | 10 | right_ankle_pitch_joint | Direct |
| 11 | R Ankle Roll | → | 11 | right_ankle_roll_joint | Direct |
| 12 | Waist Yaw | → | 12 | waist_yaw_joint | Direct |
| 13 | Waist Roll | → | 13 | waist_roll_joint | Direct |
| 14 | Waist Pitch | → | 14 | waist_pitch_joint | Direct |
| 15 | L Shoulder Pitch | → | 15 | left_shoulder_pitch_joint | Direct |
| 16 | L Shoulder Roll | → | 16 | left_shoulder_roll_joint | Direct |
| 17 | L Shoulder Yaw | → | 17 | left_shoulder_yaw_joint | Direct |
| 18 | L Elbow | → | 18 | left_elbow_joint | Direct |
| 19 | L Wrist Roll | → | 19 | left_wrist_roll_joint | Direct |
| 20 | L Wrist Pitch | → | 20 | left_wrist_pitch_joint | Direct |
| 21 | L Wrist Yaw | → | 21 | left_wrist_yaw_joint | Direct |
| 22 | R Shoulder Pitch | → | 22 | right_shoulder_pitch_joint | Direct |
| 23 | R Shoulder Roll | → | 23 | right_shoulder_roll_joint | Direct |
| 24 | R Shoulder Yaw | → | 24 | right_shoulder_yaw_joint | Direct |
| 25 | R Elbow | → | 25 | right_elbow_joint | Direct |
| 26 | R Wrist Roll | → | 26 | right_wrist_roll_joint | Direct |
| 27 | R Wrist Pitch | → | 27 | right_wrist_pitch_joint | Direct |
| 28 | R Wrist Yaw | → | 28 | right_wrist_yaw_joint | Direct |
| — | *(no hand control)* | → | 29–42 | Hand joints (14) | Set to 0.0 (neutral open hand) |

**Note on ordering:** Cosmos 3 uses hip `[yaw, roll, pitch]` ordering (common in Isaac Lab). The G1 URDF uses `[pitch, roll, yaw]` ordering. The hip joints (indices 0–2 and 6–8) need reordering. Arms follow the same `[pitch, roll, yaw]` convention in both — no reordering needed.

**Pros:**
- Simple: a permutation matrix + scaling + padding. ~50 lines of Python.
- Deterministic, no training needed.
- Works immediately once Cosmos 3 action mode is available.

**Cons:**
- Assumes the AgiBot and G1 have identical joint limit ranges and link lengths. Slight kinematic differences will cause drift.
- Hand DoF are fixed to neutral — can't use Cosmos 3 for dexterous manipulation tasks.
- No whole-body coordination optimization.

---

### Strategy B: Task-Space Abstraction (Phase 2)

**How it works:** Decode Cosmos 3's 29D joint angles into task-space targets via AgiBot Forward Kinematics, then solve G1 Inverse Kinematics.

```
Cosmos 3 29D joint angles
        │
        ▼
┌───────────────────────────┐
│ AgiBot Forward Kinematics │  (requires AgiBot URDF — can use standard humanoid model)
└───────────┬───────────────┘
            │
            ▼
Task-Space Targets (30D):
  • Left hand pose:   [x, y, z, qx, qy, qz, qw]  (7D)  — position + quaternion
  • Right hand pose:  [x, y, z, qx, qy, qz, qw]  (7D)
  • Left foot pose:   [x, y, z, qx, qy, qz, qw]  (7D)
  • Right foot pose:  [x, y, z, qx, qy, qz, qw]  (7D)
  • CoM target:       [x, y, z]                    (3D)
  • Torso orientation: [roll, pitch, yaw]           (3D)
  Total: 34D (some redundancy, compressible to ~20D)
            │
            ▼
┌───────────────────────────┐
│ G1 Inverse Kinematics     │  (part of WBC, runs on Orin NX)
│  • Prioritized QP solver  │
│  • Joint limit constraints │
│  • Self-collision avoidance│
└───────────┬───────────────┘
            │
            ▼
G1 43D joint targets
```

**Pros:**
- Embodiment-agnostic: Cosmos 3 output becomes robot-independent.
- Naturally handles kinematic differences (link lengths, joint limits).
- Hands can be controlled via task-space targets (grasp poses).
- Integrates cleanly with the Whole-Body Controller.

**Cons:**
- Requires an AgiBot kinematic model for FK (standard models exist in Isaac assets).
- IK solving adds ~1 ms latency per step (negligible at 40Hz).
- Information loss: some subtle joint-space coordination learned by Cosmos 3 may not survive the FK→IK round-trip.
- Slight trajectory deviation compared to direct joint mapping.

---

### Strategy C: Learned MLP Adapter (Phase 3)

**How it works:** Train a small neural network to directly map Cosmos 3 29D output → G1 43D targets, using paired simulation data.

```
Input: Cosmos 3 29D action + G1 current state (43D proprioception + 6D base pose) = ~78D
       │
       ▼
┌─────────────────────────────┐
│ MLP Adapter (~500K params)  │
│  • 3 hidden layers (256→512→256) │
│  • ReLU activations          │
│  • Residual connections      │
│  • Output: 43D joint targets │
└─────────────┬───────────────┘
              │
              ▼
G1 43D joint targets
```

**Training data generation:**
1. Run Cosmos 3 Policy mode on diverse tasks in Isaac Sim with the AgiBot model
2. For each Cosmos 3 action, use Strategy B (task-space) to compute a G1 target
3. Record (cosmos_action, g1_state) → (g1_target) pairs
4. Train with MSE loss + joint limit penalty + smoothness regularization

**Pros:**
- Learns G1-specific kinematics (joint limits, coupling, singularities).
- Hand dexterity: can learn to map manipulation intent to hand DoF.
- Fast inference: < 0.1 ms on RTX 5090 or Orin NX.
- Smooth trajectories (regularized).

**Cons:**
- Requires training data (can be generated synthetically in Isaac Sim).
- Black box: harder to debug than geometric approaches.
- Needs retraining if Cosmos 3 is fine-tuned or the G1 hardware changes.

---

### Strategy D: Hybrid — Remap + WBC (Recommended Production Architecture)

**How it works:** Use Strategy A for the 29 body joints, then pass through the G1 WBC as a reference trajectory. The WBC refines for balance and constraint satisfaction.

```
Cosmos 3 29D
     │
     ▼
Functional Remap (Strategy A) → 29D G1 body targets
     │
     ▼
┌────────────────────────────────┐
│ Whole-Body Controller (WBC)    │  ← Runs on Orin NX @ 500Hz
│  • QP tracking controller      │
│  • Tracks 29D body targets     │
│  • Adds balance constraints    │
│  • Joint limit enforcement      │
│  • Self-collision avoidance    │
│  • Hand controller (separate)  │
└────────────┬───────────────────┘
             │
             ▼
G1 43D motor commands @ 500Hz
```

**Pros:**
- Production-grade: WBC provides the safety net.
- Cosmos 3 sets intent; WBC handles physics.
- Hands managed by a separate grasp controller (not Cosmos 3).
- Graceful degradation: if Cosmos 3 output is invalid, WBC maintains balance.

**Cons:**
- Most complex integration.
- WBC tuning required for tracking quality vs. safety tradeoff.

---

## 4. Implementation Plan

### Phase 1: Direct Remapping (Now)

**File:** `src/action_adapter.py`

```python
import numpy as np

# Cosmos 3 (AgiBot 29D) → G1 29D body index mapping
# Cosmos order: [l_hip_yaw, l_hip_roll, l_hip_pitch, l_knee, l_ankle_pitch, l_ankle_roll,
#                r_hip_yaw, r_hip_roll, r_hip_pitch, r_knee, r_ankle_pitch, r_ankle_roll,
#                waist_yaw, waist_roll, waist_pitch,
#                l_shoulder_pitch, l_shoulder_roll, l_shoulder_yaw, l_elbow, l_wrist_roll, l_wrist_pitch, l_wrist_yaw,
#                r_shoulder_pitch, r_shoulder_roll, r_shoulder_yaw, r_elbow, r_wrist_roll, r_wrist_pitch, r_wrist_yaw]
#
# G1 order: [l_hip_pitch, l_hip_roll, l_hip_yaw, l_knee, l_ankle_pitch, l_ankle_roll,
#            r_hip_pitch, r_hip_roll, r_hip_yaw, r_knee, r_ankle_pitch, r_ankle_roll,
#            waist_yaw, waist_roll, waist_pitch,
#            l_shoulder_pitch, l_shoulder_roll, l_shoulder_yaw, l_elbow, l_wrist_roll, l_wrist_pitch, l_wrist_yaw,
#            r_shoulder_pitch, r_shoulder_roll, r_shoulder_yaw, r_elbow, r_wrist_roll, r_wrist_pitch, r_wrist_yaw]

COSMOS_TO_G1_BODY_MAP = np.array([
    # Left leg: cosmos [hip_yaw(0), hip_roll(1), hip_pitch(2)] → g1 [hip_pitch(0), hip_roll(1), hip_yaw(2)]
    2, 1, 0, 3, 4, 5,
    # Right leg: cosmos [hip_yaw(6), hip_roll(7), hip_pitch(8)] → g1 [hip_pitch(6), hip_roll(7), hip_yaw(8)]
    8, 7, 6, 9, 10, 11,
    # Waist: cosmos [yaw(12), roll(13), pitch(14)] → g1 [yaw(12), roll(13), pitch(14)]
    12, 13, 14,
    # Left arm: cosmos [shldr_p(15), shldr_r(16), shldr_y(17), elbow(18), wrist_r(19), wrist_p(20), wrist_y(21)]
    #        → g1    [shldr_p(15), shldr_r(16), shldr_y(17), elbow(18), wrist_r(19), wrist_p(20), wrist_y(21)]
    15, 16, 17, 18, 19, 20, 21,
    # Right arm: same pattern
    22, 23, 24, 25, 26, 27, 28,
])

G1_TOTAL_DOF = 43
G1_BODY_DOF = 29
G1_HAND_DOF = 14

# Neutral hand pose: fingers extended (open hand, index 0.0 = neutral/rest)
NEUTRAL_HAND_POSE = np.zeros(G1_HAND_DOF)

def cosmos_to_g1(cosmos_action_29d: np.ndarray, scale: float = 1.0) -> np.ndarray:
    """
    Convert Cosmos 3 29D AgiBot action → G1 43D joint targets.
    
    Args:
        cosmos_action_29d: Normalized action vector from Cosmos 3, shape (29,)
                           Values in [-1, 1] representing fraction of joint range.
        scale: Optional scaling factor to reduce aggressiveness (default 1.0).
    
    Returns:
        g1_targets_43d: Joint angle targets for the G1, shape (43,)
    """
    # Step 1: Remap 29 Cosmos joints → 29 G1 body joints
    g1_body_29d = cosmos_action_29d[COSMOS_TO_G1_BODY_MAP] * scale
    
    # Step 2: Pad with neutral hand positions
    g1_full_43d = np.concatenate([g1_body_29d, NEUTRAL_HAND_POSE])
    
    return g1_full_43d


def cosmos_to_g1_with_hands(
    cosmos_action_29d: np.ndarray, 
    hand_action_14d: np.ndarray = None
) -> np.ndarray:
    """
    Convert with explicit hand control from a separate grasp controller.
    """
    g1_body_29d = cosmos_action_29d[COSMOS_TO_G1_BODY_MAP]
    hand_14d = hand_action_14d if hand_action_14d is not None else NEUTRAL_HAND_POSE
    return np.concatenate([g1_body_29d, hand_14d])
```

### Phase 2: Task-Space Wrapper (Next)

Add a `TaskSpaceAdapter` that runs AgiBot FK → IK on the G1 URDF using the WBC's IK solver. This replaces the direct permutation with a geometrically correct mapping.

### Phase 3: Learned Adapter (Future)

Train the MLP using Isaac Sim rollouts once we have a working Cosmos 3 → Isaac Sim pipeline.

---

## 5. Joint Limit Comparison & Safety

### G1 Joint Limits (from config)

| Joint Group | G1 Range (rad) | Notes |
|:---|:---|:---|
| Hip Pitch | [-0.5, 2.7] | Large forward range |
| Hip Roll | [-1.0, 1.0] | Lateral swing |
| Hip Yaw | [-1.0, 1.0] | Rotation |
| Knee | [-0.5, 2.7] | Similar to hip pitch |
| Ankle Pitch | [-0.5, 1.0] | Dorsiflexion limited |
| Ankle Roll | [-0.5, 0.5] | Inversion/eversion |
| Shoulder Pitch | [-3.0, 3.0] | Full overhead reach |
| Shoulder Roll | [-1.5, 1.5] | Abduction |
| Shoulder Yaw | [-1.5, 1.5] | Humeral rotation |
| Elbow | [-2.5, 0.1] | Near-full extension |
| Wrist Roll | [-3.0, 3.0] | Pronation/supination |
| Wrist Pitch | [-1.5, 1.5] | Flexion/extension |
| Wrist Yaw | [-1.0, 1.0] | Deviation |
| Waist Yaw | [-1.5, 1.5] | Trunk rotation |
| Waist Roll | [-0.5, 0.5] | Lateral bend |
| Waist Pitch | [-1.0, 1.0] | Forward/back bend |

The Cosmos 3 actions are in `[-1, 1]` normalized space. When denormalized to the AgiBot's joint limits, they may exceed G1 limits. **Always clamp G1 targets to these limits** before sending to the WBC.

### Safety Wrapper

```python
def safe_g1_target(cosmos_action_29d: np.ndarray) -> np.ndarray:
    """Convert with joint limit clamping and velocity limiting."""
    targets = cosmos_to_g1(cosmos_action_29d)
    
    # Clamp to G1 joint limits
    targets = np.clip(targets, G1_JOINT_LOWER_LIMITS, G1_JOINT_UPPER_LIMITS)
    
    # Optional: rate-limit changes from previous command
    # delta = targets - previous_targets
    # delta = np.clip(delta, -MAX_VELOCITY * dt, MAX_VELOCITY * dt)
    # targets = previous_targets + delta
    
    return targets
```

---

## 6. Integration into the Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ RTX 5090                                                         │
│                                                                  │
│  Cosmos 3 (vLLM-Omni)                                           │
│  POST /v1/videos                                                 │
│  extra_params: {                                                 │
│    "action_mode": "policy",                                      │
│    "domain_name": "agibot_humanoid",                             │
│    "raw_action_dim": 29,                                         │
│    "action_chunk_size": 50                                       │
│  }                                                               │
│                                                                  │
│  Response: {                                                     │
│    "action": [[j0,j1,...j28], ...]  ← 50 timesteps × 29D        │
│  }                                                               │
│                         │                                        │
│                         ▼                                        │
│  ┌─────────────────────────────────────┐                        │
│  │ Action Adapter (action_adapter.py)  │                        │
│  │  • Permutation (COSMOS_TO_G1_MAP)   │                        │
│  │  • Denormalization                  │                        │
│  │  • Hand padding (neutral)           │                        │
│  │  • Joint limit clamping             │                        │
│  │  • Interpolation (50 timesteps      │                        │
│  │    → 40Hz continuous stream)        │                        │
│  └────────────────┬────────────────────┘                        │
│                   │ 43D joint targets @ 40Hz                     │
└───────────────────┼─────────────────────────────────────────────┘
                    │ Gigabit Ethernet
┌───────────────────▼─────────────────────────────────────────────┐
│ Jetson Orin NX                                                   │
│  ┌─────────────────────────────────────┐                        │
│  │ Whole-Body Controller @ 500Hz       │                        │
│  │  • Tracks 43D targets               │                        │
│  │  • Balance QP solver                │                        │
│  │  • CBF safety filter                │                        │
│  │  • Link-loss buffer                 │                        │
│  └─────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Summary & Recommendations

| Strategy | When | Complexity | Quality | Hand Support |
|:---|:---|:---|:---|:---|
| **A: Direct Remap** | Now | Low | Good (body) | Neutral only |
| **B: Task-Space** | Phase 2 | Medium | Better | Via grasp poses |
| **C: Learned MLP** | Phase 3 | Medium (training) | Best | Learned |
| **D: Hybrid + WBC** | Production | High | Production | Separate controller |

**Recommended path:**
1. **Start with Strategy A** — functional remapping. It works immediately, is safe (joint limit clamping), and lets us test Cosmos 3's action quality on the G1.
2. **Add WBC tracking (Strategy D)** — the WBC already exists in our architecture. Feed the remapped targets as reference trajectories.
3. **Transition to Task-Space (Strategy B)** if we observe kinematic drift from the AgiBot→G1 mismatch.
4. **Train the MLP (Strategy C)** once we have enough paired simulation data.

The critical unknown is **whether Cosmos 3's action mode is mature enough to output useful 29D trajectories**. Until action mode (PR #4102) is merged into vLLM-Omni and we can benchmark the output quality, Strategy A is the right starting point.
