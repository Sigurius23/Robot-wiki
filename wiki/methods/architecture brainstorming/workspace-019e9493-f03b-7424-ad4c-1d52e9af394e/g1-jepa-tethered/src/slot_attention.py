import torch
import torch.nn as nn
import torch.nn.functional as F

class SlotAttention(nn.Module):
    """
    Slot Attention module for object-centric decomposition on the Unitree G1.
    Allows the JEPA model to reason about discrete objects (slots) rather than global feature maps.
    
    Ref: Object-Centric Learning with Slot Attention (arXiv:2006.15055)
    """
    def __init__(self, num_slots, input_dim, slot_dim, iterations=3):
        super().__init__()
        self.num_slots = num_slots
        self.iterations = iterations
        self.scale = slot_dim ** -0.5

        self.slots_mu = nn.Parameter(torch.randn(1, 1, slot_dim))
        self.slots_logsigma = nn.Parameter(torch.zeros(1, 1, slot_dim))

        self.to_q = nn.Linear(slot_dim, slot_dim)
        self.to_k = nn.Linear(input_dim, slot_dim)
        self.to_v = nn.Linear(input_dim, slot_dim)

        self.gru = nn.GRUCell(slot_dim, slot_dim)
        self.norm_input = nn.LayerNorm(input_dim)
        self.norm_slots = nn.LayerNorm(slot_dim)
        self.norm_pre_ff = nn.LayerNorm(slot_dim)

    def forward(self, inputs):
        # inputs shape: [batch_size, num_inputs, input_dim]
        b, n, d = inputs.shape
        inputs = self.norm_input(inputs)
        
        k = self.to_k(inputs)
        v = self.to_v(inputs)

        # Initialize slots from a learnable distribution
        mu = self.slots_mu.expand(b, self.num_slots, -1)
        sigma = self.slots_logsigma.exp().expand(b, self.num_slots, -1)
        slots = mu + sigma * torch.randn_like(mu)

        for _ in range(self.iterations):
            slots_prev = slots
            slots = self.norm_slots(slots)
            
            q = self.to_q(slots)
            
            dots = torch.einsum('bid,bjd->bij', q, k) * self.scale
            attn = dots.softmax(dim=1) # Competition over slots
            
            # Weighted mean of values
            attn = attn + 1e-8
            attn = attn / attn.sum(dim=-1, keepdim=True)
            
            updates = torch.einsum('bij,bjd->bid', attn, v)
            
            # Recurrent update of slots
            slots = self.gru(updates.view(-1, d), slots_prev.view(-1, d))
            slots = slots.view(b, self.num_slots, d)
            
        return slots

if __name__ == "__main__":
    # Example usage:
    # inputs = torch.randn(1, 1024, 128) # 1024 Minkowski voxels
    # slot_attn = SlotAttention(num_slots=8, input_dim=128, slot_dim=128)
    # slots = slot_attn(inputs)
    print("Slot Attention Module Skeleton Loaded.")
