"""
Action Space Adapter: Cosmos 3 (29D AgiBot format) → G1 (43D)

Converts Cosmos 3's normalized 29-dimensional AgiBot humanoid action vectors
into the Unitree G1's 43-dimensional joint angle targets in radians.

Pipeline:
  1. Cosmos 3 outputs normalized actions in [-1, 1]  (29D)
  2. Remap to G1 joint ordering                     (29D, still normalized)
  3. Denormalize using G1 joint limits              (29D, radians)
  4. Pad with neutral hand positions                (43D, radians)
  5. Clamp to G1 joint limits (safety)              (43D, radians)

Strategy: Functional joint remapping with G1-limit denormalization.
See docs/ACTION_SPACE_ADAPTER.md for the full design rationale.
"""

import numpy as np
from typing import Optional

# ---------------------------------------------------------------------------
# Joint mapping: Cosmos 3 (AgiBot 29D ordering) → G1 body joint indices
#
# Cosmos ordering (Isaac Lab convention, hip=[yaw,roll,pitch]):
#   [l_hip_yaw, l_hip_roll, l_hip_pitch, l_knee, l_ankle_pitch, l_ankle_roll,
#    r_hip_yaw, r_hip_roll, r_hip_pitch, r_knee, r_ankle_pitch, r_ankle_roll,
#    waist_yaw, waist_roll, waist_pitch,
#    l_shoulder_pitch, l_shoulder_roll, l_shoulder_yaw, l_elbow,
#    l_wrist_roll, l_wrist_pitch, l_wrist_yaw,
#    r_shoulder_pitch, r_shoulder_roll, r_shoulder_yaw, r_elbow,
#    r_wrist_roll, r_wrist_pitch, r_wrist_yaw]
#
# G1 29D body ordering (from isri-aist/g1_description URDF, hip=[pitch,roll,yaw]):
#   [l_hip_pitch, l_hip_roll, l_hip_yaw, l_knee, l_ankle_pitch, l_ankle_roll,
#    r_hip_pitch, r_hip_roll, r_hip_yaw, r_knee, r_ankle_pitch, r_ankle_roll,
#    waist_yaw, waist_roll, waist_pitch,
#    l_shoulder_pitch, l_shoulder_roll, l_shoulder_yaw, l_elbow,
#    l_wrist_roll, l_wrist_pitch, l_wrist_yaw,
#    r_shoulder_pitch, r_shoulder_roll, r_shoulder_yaw, r_elbow,
#    r_wrist_roll, r_wrist_pitch, r_wrist_yaw]
#
# Key difference: hip joints are [yaw,roll,pitch] in Cosmos vs [pitch,roll,yaw] in G1.
# Arms follow the same [pitch,roll,yaw] convention in both.
# ---------------------------------------------------------------------------

COSMOS_TO_G1_BODY_MAP = np.array([
    # Left leg: cosmos[yaw,roll,pitch] → g1[pitch,roll,yaw]
    2, 1, 0,   # hip: yaw→pitch(2), roll→roll(1), pitch→yaw(0)
    3, 4, 5,   # knee, ankle_pitch, ankle_roll (direct)
    # Right leg: cosmos[yaw,roll,pitch] → g1[pitch,roll,yaw]
    8, 7, 6,   # hip: yaw→pitch(8), roll→roll(7), pitch→yaw(6)
    9, 10, 11, # knee, ankle_pitch, ankle_roll (direct)
    # Waist: [yaw, roll, pitch] → [yaw, roll, pitch] (direct)
    12, 13, 14,
    # Left arm: [shldr_p, shldr_r, shldr_y, elbow, wrist_r, wrist_p, wrist_y] (direct)
    15, 16, 17, 18, 19, 20, 21,
    # Right arm: (direct)
    22, 23, 24, 25, 26, 27, 28,
], dtype=np.int32)

# Inverse mapping for debugging: G1 body index → Cosmos index
G1_TO_COSMOS_BODY_MAP = np.zeros(29, dtype=np.int32)
for cosmos_idx, g1_idx in enumerate(COSMOS_TO_G1_BODY_MAP):
    G1_TO_COSMOS_BODY_MAP[g1_idx] = cosmos_idx

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------

COSMOS_ACTION_DIM = 29
G1_BODY_DOF = 29
G1_HAND_DOF = 14
G1_TOTAL_DOF = G1_BODY_DOF + G1_HAND_DOF  # 43

# ---------------------------------------------------------------------------
# G1 Joint Limits (radians)
# Source: Unitree G1 EDU specifications, isri-aist/g1_description URDF
# Hand limits are approximate — pending verification against Dex3-1 specs.
# ---------------------------------------------------------------------------

G1_JOINT_LOWER_LIMITS = np.array([
    # Left leg (6)
    -0.5,  -1.0,  -1.0,  -0.5,  -0.5,  -0.5,
    # Right leg (6)
    -0.5,  -1.0,  -1.0,  -0.5,  -0.5,  -0.5,
    # Waist (3)
    -1.5,  -0.5,  -1.0,
    # Left arm (7)
    -3.0,  -1.5,  -1.5,  -2.5,  -3.0,  -1.5,  -1.0,
    # Right arm (7)
    -3.0,  -1.5,  -1.5,  -2.5,  -3.0,  -1.5,  -1.0,
    # Left hand (7) — APPROXIMATE (Dex3-1: thumb 3 DoF, index 2, middle 2)
    -0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1,
    # Right hand (7) — APPROXIMATE
    -0.1, -0.1, -0.1, -0.1, -0.1, -0.1, -0.1,
], dtype=np.float64)

G1_JOINT_UPPER_LIMITS = np.array([
    # Left leg (6)
    2.7,  1.0,  1.0,  2.7,  1.0,  0.5,
    # Right leg (6)
    2.7,  1.0,  1.0,  2.7,  1.0,  0.5,
    # Waist (3)
    1.5,  0.5,  1.0,
    # Left arm (7)
    3.0,  1.5,  1.5,  0.1,  3.0,  1.5,  1.0,
    # Right arm (7)
    3.0,  1.5,  1.5,  0.1,  3.0,  1.5,  1.0,
    # Left hand (7) — APPROXIMATE
    2.0,  2.0,  2.0,  2.0,  2.0,  2.0,  2.0,
    # Right hand (7) — APPROXIMATE
    2.0,  2.0,  2.0,  2.0,  2.0,  2.0,  2.0,
], dtype=np.float64)

# Precomputed for denormalization: midpoints and half-ranges
_G1_BODY_MID = (G1_JOINT_LOWER_LIMITS[:G1_BODY_DOF] + G1_JOINT_UPPER_LIMITS[:G1_BODY_DOF]) / 2.0
_G1_BODY_HALF_RANGE = (G1_JOINT_UPPER_LIMITS[:G1_BODY_DOF] - G1_JOINT_LOWER_LIMITS[:G1_BODY_DOF]) / 2.0

# Neutral hand pose: fingers extended (open hand, 0.0 rad = neutral/rest)
NEUTRAL_HAND_POSE = np.zeros(G1_HAND_DOF, dtype=np.float64)

# Safety: validate inputs for NaN/inf.
# Set to False in production only if you've verified Cosmos 3 output quality
# and need the microsecond-level speedup.
_VALIDATE_INPUTS = True


# ---------------------------------------------------------------------------
# Core adapter functions
# ---------------------------------------------------------------------------

def _check_finite(arr: np.ndarray, label: str) -> None:
    """Raise ValueError if array contains NaN or inf values."""
    if not np.isfinite(arr).all():
        nan_count = int(np.isnan(arr).sum())
        inf_count = int(np.isinf(arr).sum())
        raise ValueError(
            f"{label} contains invalid values: "
            f"{nan_count} NaN(s), {inf_count} inf(s)"
        )


def cosmos_to_g1_body(
    cosmos_action: np.ndarray,
    denormalize: bool = True,
) -> np.ndarray:
    """
    Remap Cosmos 3 29D AgiBot action → G1 29D body joint ordering,
    optionally denormalizing from [-1, 1] to radian joint angles.

    The only reordering needed is the hip joints:
    Cosmos uses [yaw, roll, pitch]; G1 uses [pitch, roll, yaw].

    Args:
        cosmos_action: Cosmos 3 action vector, shape (29,).
        denormalize: If True (default), convert normalized [-1, 1] values
                     to radian joint angles using G1 joint limits.
                     If False, output remains in [-1, 1] space.

    Returns:
        g1_body_29d: G1-ordered joint values, shape (29,).
                     In radians if denormalize=True, else in [-1, 1].
    """
    if _VALIDATE_INPUTS:
        _check_finite(cosmos_action, "cosmos_action")

    if cosmos_action.shape != (COSMOS_ACTION_DIM,):
        raise ValueError(
            f"Expected cosmos_action shape ({COSMOS_ACTION_DIM},), "
            f"got {cosmos_action.shape}"
        )

    # Permute Cosmos indices → G1 indices
    g1_body = cosmos_action[COSMOS_TO_G1_BODY_MAP]

    if denormalize:
        # Convert normalized [-1, 1] → radians using G1 joint limits
        g1_body = _G1_BODY_MID + g1_body * _G1_BODY_HALF_RANGE

    return g1_body


def cosmos_to_g1_full(
    cosmos_action: np.ndarray,
    hand_action: Optional[np.ndarray] = None,
    clamp: bool = True,
) -> np.ndarray:
    """
    Convert Cosmos 3 29D normalized action → G1 43D joint targets (radians).

    Full pipeline: remap → denormalize → pad hands → clamp.

    Args:
        cosmos_action: Cosmos 3 action vector, shape (29,), values in [-1, 1].
        hand_action: Optional hand joint targets in radians, shape (14,).
                     If None, hands are set to neutral (open) position.
        clamp: If True (default), clamp outputs to G1 joint limits.

    Returns:
        g1_targets: Full 43D joint angle targets in radians.
    """
    if _VALIDATE_INPUTS:
        _check_finite(cosmos_action, "cosmos_action")

    # Body: remap + denormalize (Cosmos [-1,1] → G1 radians)
    body = cosmos_to_g1_body(cosmos_action, denormalize=True)

    # Hands: use provided or neutral (already in radians)
    hands = (
        hand_action.copy()
        if hand_action is not None
        else NEUTRAL_HAND_POSE.copy()
    )

    if hands.shape != (G1_HAND_DOF,):
        raise ValueError(
            f"Expected hand_action shape ({G1_HAND_DOF},), got {hands.shape}"
        )

    if _VALIDATE_INPUTS and hand_action is not None:
        _check_finite(hands, "hand_action")

    full = np.concatenate([body, hands], axis=-1)

    if clamp:
        full = np.clip(full, G1_JOINT_LOWER_LIMITS, G1_JOINT_UPPER_LIMITS)

    return full


def cosmos_chunk_to_g1(
    cosmos_chunk: np.ndarray,
    clamp: bool = True,
) -> np.ndarray:
    """
    Convert a chunk (batch) of Cosmos 3 actions → G1 43D targets.

    Args:
        cosmos_chunk: Shape (T, 29) — T timesteps of Cosmos 3 actions,
                      each in [-1, 1].
        clamp: Joint limit clamping (default True).

    Returns:
        g1_chunk: Shape (T, 43) — G1 joint angle targets (radians).
    """
    if cosmos_chunk.ndim != 2 or cosmos_chunk.shape[1] != COSMOS_ACTION_DIM:
        raise ValueError(
            f"Expected cosmos_chunk shape (T, {COSMOS_ACTION_DIM}), "
            f"got {cosmos_chunk.shape}"
        )

    T = cosmos_chunk.shape[0]
    g1_chunk = np.zeros((T, G1_TOTAL_DOF), dtype=np.float64)

    for t in range(T):
        g1_chunk[t] = cosmos_to_g1_full(cosmos_chunk[t], clamp=clamp)

    return g1_chunk


# ---------------------------------------------------------------------------
# Inverse mapping: G1 → Cosmos (for debugging / trajectory logging)
# ---------------------------------------------------------------------------

def g1_body_to_cosmos(
    g1_body: np.ndarray,
    normalize: bool = True,
) -> np.ndarray:
    """
    Convert G1 29D body joint state (radians) back to Cosmos 3 ordering.
    Useful for logging and comparing expected vs. actual trajectories.
    """
    if g1_body.shape != (G1_BODY_DOF,):
        raise ValueError(f"Expected g1_body shape ({G1_BODY_DOF},)")

    cosmos = g1_body[G1_TO_COSMOS_BODY_MAP]

    if normalize:
        # Normalize back to [-1, 1] using G1 limits
        g1_mid = _G1_BODY_MID[G1_TO_COSMOS_BODY_MAP]
        g1_hr = _G1_BODY_HALF_RANGE[G1_TO_COSMOS_BODY_MAP]
        cosmos = (cosmos - g1_mid) / g1_hr

    return cosmos


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_mapping() -> bool:
    """Verify that the mapping matrices are correct bijections."""
    # Every Cosmos index should map to exactly one G1 index (0..28)
    mapped = set(COSMOS_TO_G1_BODY_MAP)
    assert mapped == set(range(G1_BODY_DOF)), \
        f"COSMOS_TO_G1_BODY_MAP is not a bijection: missing {set(range(G1_BODY_DOF)) - mapped}"

    # Round-trip test (normalized space)
    rng = np.random.default_rng(42)
    test_action = rng.uniform(-1, 1, size=COSMOS_ACTION_DIM)
    g1 = cosmos_to_g1_body(test_action, denormalize=False)
    back = g1_body_to_cosmos(g1, normalize=False)
    assert np.allclose(test_action, back, atol=1e-10), \
        f"Round-trip failed: max diff = {np.abs(test_action - back).max():.2e}"

    # Denormalization round-trip
    g1_rad = cosmos_to_g1_body(test_action, denormalize=True)
    back_norm = g1_body_to_cosmos(g1_rad, normalize=True)
    assert np.allclose(test_action, back_norm, atol=1e-6), \
        f"Denorm round-trip failed: max diff = {np.abs(test_action - back_norm).max():.2e}"

    return True


if __name__ == "__main__":
    assert validate_mapping(), "Mapping validation failed"

    # Example: convert a random Cosmos 3 action (normalized [-1, 1])
    rng = np.random.default_rng(123)
    cosmos_test = rng.uniform(-1, 1, size=(COSMOS_ACTION_DIM,))
    g1_targets = cosmos_to_g1_full(cosmos_test, clamp=True)

    print(f"Cosmos 3 input:     {cosmos_test.shape}  range=[{cosmos_test.min():.3f}, {cosmos_test.max():.3f}] (normalized)")
    print(f"G1 body output:     {g1_targets[:29].shape} range=[{g1_targets[:29].min():.3f}, {g1_targets[:29].max():.3f}] rad")
    print(f"G1 hand output:     {g1_targets[29:].shape} neutral={np.allclose(g1_targets[29:], 0.0)}")
    print(f"All within limits:  {np.all(g1_targets >= G1_JOINT_LOWER_LIMITS) and np.all(g1_targets <= G1_JOINT_UPPER_LIMITS)}")
    print("✓ Adapter self-test passed")
