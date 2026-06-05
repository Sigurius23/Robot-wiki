import torch
import torch.nn as nn
import torch.nn.functional as F

class VICRegLoss(nn.Module):
    """
    Variance-Invariance-Covariance Regularization Loss for JEPA.
    Prevents representational collapse without needing negative pairs.
    
    Ref: VICReg (arXiv:2105.04906)
    """
    def __init__(self, sim_coeff=25.0, std_coeff=25.0, cov_coeff=1.0):
        super().__init__()
        self.sim_coeff = sim_coeff
        self.std_coeff = std_coeff
        self.cov_coeff = cov_coeff

    def forward(self, x, y):
        # x, y: [Batch, Latent_Dim]
        # x is the current state embedding, y is the predicted future state or second view.
        
        # 1. Invariance Loss (Mean Squared Error)
        repr_loss = F.mse_loss(x, y)

        # 2. Variance Loss (Hinge loss on Standard Deviation)
        # We want the std of each feature across the batch to be at least 1.0
        std_x = torch.sqrt(x.var(dim=0) + 0.0001)
        std_y = torch.sqrt(y.var(dim=0) + 0.0001)
        std_loss = torch.mean(F.relu(1.0 - std_x)) + torch.mean(F.relu(1.0 - std_y))

        # 3. Covariance Loss (Off-diagonal decorrelation)
        # Prevents different dimensions from encoding the same information.
        num_features = x.shape[1]
        x = x - x.mean(dim=0)
        y = y - y.mean(dim=0)
        
        cov_x = (x.T @ x) / (x.shape[0] - 1)
        cov_y = (y.T @ y) / (y.shape[0] - 1)
        
        cov_loss = off_diagonal(cov_x).pow_(2).sum().div(num_features) + \
                   off_diagonal(cov_y).pow_(2).sum().div(num_features)

        weighted_loss = self.sim_coeff * repr_loss + \
                        self.std_coeff * std_loss + \
                        self.cov_coeff * cov_loss
        return weighted_loss

def off_diagonal(x):
    n, m = x.shape
    assert n == m
    return x.flatten()[:-1].view(n - 1, n + 1)[:, 1:].flatten()

if __name__ == "__main__":
    # Example usage:
    # criterion = VICRegLoss()
    # z1 = torch.randn(32, 512)
    # z2 = torch.randn(32, 512)
    # loss = criterion(z1, z2)
    print("VICReg Loss Module Skeleton Loaded.")
