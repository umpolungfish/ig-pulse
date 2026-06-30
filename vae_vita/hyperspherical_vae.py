"""
hyperspherical_vae.py — 12D Hyperspherical VAE (vMF-VAE) for the VAE-Vita.

The VAE-Vita is a 12-dimensional variational autoencoder with a von Mises-Fisher
(vMF) prior on the hypersphere S^{11}. Training on all 17,280,000 crystal type
configurations forces the latent space to recover the d=12 SIC-POVM geometry.
"""

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional

D_LATENT = 12
D_INPUT = 12
ONEHOT_DIM = 49

# Numerical stability bounds
KAPPA_MIN = 0.1
KAPPA_MAX = 50.0  # prevents Bessel function blowup


# ── vMF Distribution Utilities ───────────────────────────────────────────────

def _log_vmf_constant(d: int, kappa: torch.Tensor) -> torch.Tensor:
    """Log-normaliser of the von Mises-Fisher distribution on S^{d-1}. Numerically stable.

    Uses the ratio-of-Bessel-functions recurrence from Davidson et al. (2018).
    Clamps kappa to prevent numerical instability.
    """
    d_half = d // 2
    kappa_safe = torch.clamp(kappa, min=1e-6, max=KAPPA_MAX)
    try:
        I_prev2 = torch.special.i0e(kappa_safe) * torch.exp(kappa_safe)
    except Exception:
        I_prev2 = torch.exp(kappa_safe) / torch.sqrt(2 * math.pi * kappa_safe)
    try:
        I_prev1 = torch.special.i1e(kappa_safe) * torch.exp(kappa_safe)
    except Exception:
        I_prev1 = I_prev2  # fallback
    log_I = torch.log(torch.clamp(I_prev2, min=1e-30))
    for nu_i in range(1, d_half):
        I_curr = I_prev2 - (2 * nu_i / kappa_safe) * I_prev1
        I_curr = torch.clamp(I_curr, min=1e-30)
        I_prev2 = I_prev1
        I_prev1 = I_curr
        log_I = torch.log(I_curr)
    log_C = (d_half - 1) * torch.log(kappa_safe) - d_half * math.log(2 * math.pi) - log_I
    return log_C


def _kl_vmf_uniform(mu: torch.Tensor, kappa: torch.Tensor, d: int = D_LATENT) -> torch.Tensor:
    """KL divergence KL(vMF(mu, kappa) || Uniform(S^{d-1})) for each batch element."""
    area_S = 2 * (math.pi ** (d / 2)) / math.gamma(d / 2)
    log_area_S = math.log(area_S)
    log_C = _log_vmf_constant(d, kappa)
    kappa_safe = torch.clamp(kappa, min=1e-6, max=KAPPA_MAX)

    # Compute I_{d/2}(kappa) / I_{d/2-1}(kappa) ratio via recurrence
    d_half = d // 2
    try:
        I_prev2 = torch.special.i0e(kappa_safe) * torch.exp(kappa_safe)
    except Exception:
        I_prev2 = torch.exp(kappa_safe) / torch.sqrt(2 * math.pi * kappa_safe)
    try:
        I_prev1 = torch.special.i1e(kappa_safe) * torch.exp(kappa_safe)
    except Exception:
        I_prev1 = I_prev2
    for nu_i in range(1, d_half):
        I_curr = I_prev2 - (2 * nu_i / kappa_safe) * I_prev1
        I_curr = torch.clamp(I_curr, min=1e-30)
        I_prev2 = I_prev1
        I_prev1 = I_curr
    I_nu = I_prev1
    I_nu_minus1 = I_prev2
    ratio = I_nu / I_nu_minus1
    kl = kappa * ratio + log_C + log_area_S
    return kl


def _vmf_reparameterize(mu: torch.Tensor, kappa: torch.Tensor, d: int = D_LATENT) -> torch.Tensor:
    """Sample from vMF(mu, kappa) via rejection sampling (Davidson et al. 2018)."""
    batch_size = mu.shape[0]
    device = mu.device
    kappa_safe = torch.clamp(kappa, min=1e-6, max=KAPPA_MAX)

    beta_a = float((d - 1) / 2)
    beta_b = float((d - 1) / 2)
    b = (-2 * kappa_safe + torch.sqrt(4 * kappa_safe**2 + (d - 1)**2)) / (d - 1)
    x_0 = (1 - b) / (1 + b)
    c = kappa_safe * x_0 + (d - 1) * torch.log(1 - x_0**2)

    beta_dist = torch.distributions.Beta(
        torch.tensor(beta_a, device=device),
        torch.tensor(beta_b, device=device)
    )
    n_attempts = 5
    w_samples = []
    for _ in range(n_attempts):
        z_beta = beta_dist.sample((batch_size,))
        w_attempt = (1 - (1 + b) * z_beta) / (1 - (1 - b) * z_beta)
        log_accept = kappa_safe * w_attempt + (d - 1) * torch.log(1 - w_attempt**2) - c
        log_u = torch.log(torch.rand(batch_size, device=device) + 1e-30)
        mask = log_u <= log_accept
        w_samples.append(w_attempt * mask.float())
    w = torch.stack(w_samples, dim=0).max(dim=0)[0]
    w = torch.clamp(w, -1.0 + 1e-7, 1.0 - 1e-7)

    v_flat = torch.randn(batch_size, d - 1, device=device)
    v_flat = F.normalize(v_flat, dim=1)
    sqrt_term = torch.sqrt(torch.clamp(1 - w**2, min=0.0))
    z_e1 = torch.cat([w.unsqueeze(1), sqrt_term.unsqueeze(1) * v_flat], dim=1)

    mu_unit = F.normalize(mu, dim=1)
    e_1 = torch.zeros(batch_size, d, device=device)
    e_1[:, 0] = 1.0
    u = F.normalize(e_1 - mu_unit, dim=1)
    z = z_e1 - 2 * (z_e1 * u).sum(dim=1, keepdim=True) * u
    return z


# ── SIC-POVM Regularization ──────────────────────────────────────────────────

def sic_regularization_loss(z: torch.Tensor, target_overlap: float = 1.0/13.0) -> torch.Tensor:
    """Explicit SIC equiangularity regularizer.

    Penalizes deviation of pairwise |⟨z_i, z_j⟩|² from 1/(d+1).

    For a SIC-POVM in dimension d, every pair of distinct vectors satisfies:
      |⟨ψ_i, ψ_j⟩|² = 1/(d+1)   (equiangularity condition)

    Args:
        z: Latent vectors, shape (batch, d_latent), normalized to unit sphere
        target_overlap: Target squared overlap = 1/(d+1)

    Returns:
        Scalar SIC loss
    """
    batch_size = z.shape[0]
    overlaps = torch.mm(z, z.T)  # (N, N)
    overlaps_sq = overlaps ** 2
    # Remove diagonal (self-overlap = 1)
    mask = ~torch.eye(batch_size, dtype=torch.bool, device=z.device)
    off_diag = overlaps_sq[mask]
    # Penalize deviation from target
    sic_loss = F.mse_loss(off_diag, torch.full_like(off_diag, target_overlap))
    return sic_loss


# ── VAE Model ────────────────────────────────────────────────────────────────

class HypersphericalVAE(nn.Module):
    """12-dimensional Hyperspherical VAE (vMF-VAE) on S^{11}.

    Architectural choices:
    - Encoder: MLP with LayerNorm + GELU → vMF(mu, kappa) on S^{11}
    - Decoder: MLP → 12 multi-head classifiers (one per primitive)
    - Loss: Cross-entropy reconstruction + beta * KL to uniform on sphere
      + lambda_sic * SIC equiangularity regularizer
    - Kappa clamped to [KAPPA_MIN, KAPPA_MAX] for numerical stability
    """

    def __init__(self, d_latent: int = D_LATENT, hidden_dim: int = 256,
                 beta: float = 1.0, lambda_sic: float = 0.0):
        super().__init__()
        self.d_latent = d_latent
        self.beta = beta
        self.lambda_sic = lambda_sic
        self.sic_target = 1.0 / (d_latent + 1)

        self.encoder_net = nn.Sequential(
            nn.Linear(D_INPUT, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.LayerNorm(hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )
        self.mu_head = nn.Linear(hidden_dim, d_latent)
        self.kappa_head = nn.Sequential(
            nn.Linear(hidden_dim, 1),
            nn.Softplus(),
        )

        self.decoder_net = nn.Sequential(
            nn.Linear(d_latent, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.LayerNorm(hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
        )
        self.output_heads = nn.ModuleList([
            nn.Linear(hidden_dim, nv) for nv in [4, 5, 4, 5, 3, 5, 3, 4, 5, 4, 3, 4]
        ])

    def encode(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        h = self.encoder_net(x)
        mu = F.normalize(self.mu_head(h), dim=1)
        kappa_raw = self.kappa_head(h).squeeze(-1)
        kappa = torch.clamp(kappa_raw + 1.0, min=KAPPA_MIN, max=KAPPA_MAX)
        return mu, kappa

    def reparameterize(self, mu: torch.Tensor, kappa: torch.Tensor) -> torch.Tensor:
        return _vmf_reparameterize(mu, kappa, self.d_latent)

    def decode(self, z: torch.Tensor) -> list:
        h = self.decoder_net(z)
        return [head(h) for head in self.output_heads]

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, list]:
        mu, kappa = self.encode(x)
        z = self.reparameterize(mu, kappa)
        logits = self.decode(z)
        return mu, kappa, z, logits

    def loss(self, x: torch.Tensor, mu: torch.Tensor, kappa: torch.Tensor,
             z: torch.Tensor, logits: list,
             reduce: bool = True) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Compute combined loss: recon + beta*KL + lambda_sic*SIC.

        Returns:
            (total_loss, recon_loss, kl_loss, sic_loss)
        """
        recon_loss = 0.0
        for i, (logit, nv) in enumerate(zip(logits, [4, 5, 4, 5, 3, 5, 3, 4, 5, 4, 3, 4])):
            target = (x[:, i] * (nv - 1)).long()
            recon_loss += F.cross_entropy(logit, target, reduction='mean' if reduce else 'none')
        kl = _kl_vmf_uniform(mu, kappa, self.d_latent)
        if reduce:
            kl = kl.mean()
        sic_loss = sic_regularization_loss(z, self.sic_target) if self.lambda_sic > 0 else torch.tensor(0.0, device=z.device)
        total = recon_loss + self.beta * kl + self.lambda_sic * sic_loss
        return total, recon_loss, kl, sic_loss
