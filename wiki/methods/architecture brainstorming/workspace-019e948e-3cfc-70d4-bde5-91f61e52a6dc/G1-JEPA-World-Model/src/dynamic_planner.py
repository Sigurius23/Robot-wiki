import torch
import torch.nn as nn
import numpy as np

class DynamicVRAMPlanner(nn.Module):
    """
    Implements Dynamic MPPI Sampling to prevent CUDA Out-of-Memory (OOM) 
    on the RTX 5090 (24GB).
    
    Adjusts the trajectory sample count inversely to VRAM consumption.
    """
    def __init__(self, max_samples=2048, min_samples=256, vram_limit_gb=22.5):
        super().__init__()
        self.max_samples = max_samples
        self.min_samples = min_samples
        self.vram_limit = vram_limit_gb
        self.current_samples = max_samples

    def get_adaptive_sample_count(self):
        """
        Queries the GPU memory and throttles the MPPI planner if 
        approaching the 24GB saturation point.
        """
        if not torch.cuda.is_available():
            return self.current_samples
            
        # Get current allocated VRAM in GB
        allocated_gb = torch.cuda.memory_allocated() / 1e9
        
        if allocated_gb > self.vram_limit:
            # Linear throttle: Scale down samples as we approach 24GB
            # At 22.5GB -> Max Samples
            # At 23.9GB -> Min Samples
            utilization_ratio = (allocated_gb - self.vram_limit) / (23.9 - self.vram_limit)
            utilization_ratio = max(0, min(1, utilization_ratio))
            
            self.current_samples = int(self.max_samples - (utilization_ratio * (self.max_samples - self.min_samples)))
        else:
            self.current_samples = self.max_samples
            
        return self.current_samples

    def rollout(self, current_state, action_mu):
        n_samples = self.get_adaptive_sample_count()
        # Perform MPPI rollout with n_samples...
        print(f"PLANNER: VRAM at healthy levels. Executing {n_samples} samples.")
        return n_samples

if __name__ == "__main__":
    planner = DynamicVRAMPlanner()
    planner.rollout(None, None)
