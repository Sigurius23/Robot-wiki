import time
import numpy as np
import unittest
import sys
import os

# Ensure the src directory is in the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.tether_safety import TrajectoryBuffer

class TestTrajectoryBuffer(unittest.TestCase):
    def setUp(self):
        # 500ms buffer, 5ms dt (200Hz WBC) -> 100 frames
        self.buffer = TrajectoryBuffer(buffer_size_ms=500, dt_ms=5)
        self.nominal_velocity = 1.5  # m/s

    def _generate_mock_trajectory(self, num_frames=100):
        """Generates a list of mock state dictionaries representing a forward step."""
        return [{'velocity': np.array([self.nominal_velocity, 0.0, 0.0]), 'com_pos': np.array([0.0, 0.0, 0.85]), 'yaw': 0.0} for _ in range(num_frames)]

    def test_nominal_operation(self):
        """Test that the buffer returns nominal velocities when the link is healthy."""
        traj = self._generate_mock_trajectory()
        self.buffer.update_trajectory(traj)
        
        current_state = {'velocity': np.array([self.nominal_velocity, 0.0, 0.0]), 'com_pos': np.array([0.0, 0.0, 0.85])}
        next_state = self.buffer.get_next_state(current_state)
        
        np.testing.assert_array_equal(next_state['velocity'], np.array([self.nominal_velocity, 0.0, 0.0]))

    def test_link_loss_decay(self):
        """Test that velocity decays linearly when the network drops."""
        traj = self._generate_mock_trajectory(100) # Full 500ms buffer
        self.buffer.update_trajectory(traj)
        
        # Artificially age the heartbeat to trigger link-loss (50ms watchdog)
        self.buffer.last_heartbeat = time.time() - 0.051 
        
        current_state = {'velocity': np.array([self.nominal_velocity, 0.0, 0.0]), 'com_pos': np.array([0.0, 0.0, 0.85])}
        
        # Check first frame of decay (should be < nominal)
        state_1 = self.buffer.get_next_state(current_state)
        self.assertTrue(np.linalg.norm(state_1['velocity']) < self.nominal_velocity)
        
        # Burn through 50 frames (250ms elapsed)
        state_mid = None
        for _ in range(50):
            state_mid = self.buffer.get_next_state(current_state)
            
        # Velocity should be roughly halved (at 50% of buffer)
        self.assertAlmostEqual(np.linalg.norm(state_mid['velocity']), self.nominal_velocity * 0.5, delta=0.1)

    def test_buffer_exhaustion_lock(self):
        """Test that the robot enters a safe stance when the buffer runs dry."""
        traj = self._generate_mock_trajectory(10) # Only 50ms of buffer provided
        self.buffer.update_trajectory(traj)
        
        self.buffer.last_heartbeat = time.time() - 0.051
        current_state = {'velocity': np.array([0.15, 0.0, 0.0]), 'com_pos': np.array([0.0, 0.0, 0.85])}
        
        # Exhaust the 10 frames
        for _ in range(10):
            self.buffer.get_next_state(current_state)
            
        # 11th call should trigger the zero-velocity double-support lock
        final_state = self.buffer.get_next_state(current_state)
        
        self.assertEqual(np.linalg.norm(final_state['velocity']), 0.0)
        self.assertTrue(final_state['com_pos'][2] < 0.85) # Checks for CoM lowering

if __name__ == '__main__':
    unittest.main()
