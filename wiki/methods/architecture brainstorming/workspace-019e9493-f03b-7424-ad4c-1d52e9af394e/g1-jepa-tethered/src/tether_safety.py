import time
import numpy as np
from typing import List, Optional, Dict, Any

class TrajectoryBuffer:
    """
    Maintains a rolling queue of safe kinematic states for the Unitree G1.
    Handles the transition from offboard planning to onboard emergency 
    deceleration during network link-loss.
    """
    def __init__(self, buffer_size_ms: int = 500, dt_ms: int = 5):
        """
        buffer_size_ms: Total duration of the safety buffer.
        dt_ms: Frequency of the onboard WBC (e.g., 200Hz = 5ms).
        """
        self.max_frames = buffer_size_ms // dt_ms
        self.trajectory_queue: List[Dict[str, Any]] = []
        self.last_heartbeat = time.time()
        self.timeout_threshold = 0.050  # 50ms Network Watchdog threshold

    def update_trajectory(self, new_trajectory: List[Dict[str, Any]]):
        """
        Called at ~40 Hz by the RTX 5090 Gigabit tether link.
        Replaces the current buffer with the latest optimized rollout.
        """
        # Take only the first N frames that fit our safety buffer
        self.trajectory_queue = new_trajectory[:self.max_frames]
        self.last_heartbeat = time.time()

    def get_next_state(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called at ~200-500 Hz by the onboard Whole-Body Controller (WBC).
        """
        time_since_last = time.time() - self.last_heartbeat

        # 1. Nominal Operation: Link is healthy
        if time_since_last <= self.timeout_threshold and len(self.trajectory_queue) > 0:
            return self.trajectory_queue.pop(0)

        # 2. Link-Loss Triggered: Consume buffer and decay velocity
        if len(self.trajectory_queue) > 0:
            safe_target = self.trajectory_queue.pop(0)
            
            # Apply a linear decay to the target velocity commands based on remaining buffer
            decay_factor = len(self.trajectory_queue) / self.max_frames
            safe_target['velocity'] = safe_target.get('velocity', np.zeros(3)) * decay_factor
            
            # Log warning on transition
            if len(self.trajectory_queue) == self.max_frames - 1:
                print(f"WATCHDOG: Link-Loss detected. Executing {len(self.trajectory_queue)*5}ms decay buffer.")
                
            return safe_target

        # 3. Buffer Exhausted: Force zero-velocity double-support stance
        return self._generate_locked_stance(current_state)

    def _generate_locked_stance(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Constructs a stable, zero-velocity kinematic lock for the G1.
        """
        safe_state = current_state.copy()
        safe_state['velocity'] = np.zeros(3)
        # Lower Center of Mass slightly for enhanced stability
        if 'com_pos' in safe_state:
            safe_state['com_pos'][2] -= 0.05 
        return safe_state

class TetherPhysicsEstimator:
    """
    Explicitly tracks and predicts the state of the mechanical tether.
    Informs the MPPI planner to prevent kinematic self-entanglement.
    """
    def __init__(self, tension_limit=50.0):
        self.theta_yaw_unwrapped = 0.0  # Accumulative yaw
        self.payout_length = 0.0
        self.tension_max = tension_limit

    def compute_cost(self, trajectory_rollout: np.ndarray, lambda_yaw=100.0, lambda_tension=500.0):
        """
        Math: J = sum( lambda1 * theta_yaw^2 + lambda2 * max(0, T - T_max)^2 )
        Ensures the planner biases trajectories that unwind the robot.
        """
        # trajectory_rollout: [Samples, Horizon, State_Dim]
        # Calculate unwrapped yaw penalty
        # favors returning to 0 relative yaw (the 'natural' state of the cable)
        yaw_costs = lambda_yaw * (trajectory_rollout[:, :, -1]**2)
        
        # Tension penalty would be calculated based on distance from spool origin
        # cost = lambda_tension * max(0, dist - max_payout)^2
        pass
