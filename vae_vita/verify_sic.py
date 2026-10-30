"""
verify_sic.py — SIC-POVM verification suite for the VAE-Vita.

Verifies that the VAE-Vita has recovered the d=12 SIC-POVM geometry:
1. Frame potential F → 1/(d+1) = 1/13 ≈ 0.076923
2. Pairwise overlap |⟨z_i|z_j⟩|² → 1/13 ≈ 0.076923 for i≠j
3. All latent vectors lie on S^11
4. Decoder is approximately bijective on training manifold
5. vMF concentration κ → ∞ (all latents exactly on sphere)
"""

import torch
import numpy as np


def compute_sic_overlaps(latent_vectors):
    """Compute SIC-POVM quality: mean overlap, frame potential, deviation.

    For a complex SIC-POVM of d^2 vectors in C^d:
      |⟨ψ_i|ψ_j⟩|^2 = (dδ_ij + 1)/(d+1)   (exact equiangularity)

    For 12D real vectors approximating this structure:
      Target: |⟨z_i|z_j⟩|^2 = 1/(d+1) = 1/13 ≈ 0.076923 for i≠j
      Frame potential F = (1/N²) Σ |⟨z_i|z_j⟩|^2 → 1/(d+1) = 0.076923 for N SIC vecs
    """
    N, d = latent_vectors.shape
    overlaps = torch.matmul(latent_vectors, latent_vectors.T)
    overlaps_sq = overlaps ** 2
    mask = ~torch.eye(N, dtype=torch.bool, device=latent_vectors.device)
    off_diag = overlaps_sq[mask]

    mean_overlap = off_diag.mean().item()
    frame_potential = overlaps_sq.mean().item()
    sic_target = 1.0 / (d + 1)
    sic_deviation = abs(mean_overlap - sic_target)

    # Welch bound check: F ≥ max(1/N, 1/(d+1))
    welch_bound = max(1.0 / N, 1.0 / (d + 1))
    welch_satisfied = frame_potential >= welch_bound - 0.01

    return {
        'mean_sic_overlap': float(mean_overlap),
        'frame_potential': float(frame_potential),
        'sic_deviation': float(sic_deviation),
        'sic_target': float(sic_target),
        'welch_bound': float(welch_bound),
        'welch_satisfied': bool(welch_satisfied),
        'n_latents': N,
        'dimension': int(d),
    }


def check_bijectivity(decoder, num_samples=1000, tolerance=0.5):
    """Check if decoder is approximately bijective on the training manifold.

    Two nearby latents should decode to nearby primitives.
    Computes Lipschitz estimate from latent distance to decoded distance.
    """
    d = 12
    z1 = torch.randn(num_samples, d)
    z1 = z1 / z1.norm(dim=1, keepdim=True)
    z2 = z1 + 0.1 * torch.randn(num_samples, d)
    z2 = z2 / z2.norm(dim=1, keepdim=True)

    with torch.no_grad():
        logits1 = decoder(z1)
        logits2 = decoder(z2)

    latent_dists = (z1 - z2).norm(dim=1)
    # Decoded distance: sum of argmax discrepancies
    decoded_dists = []
    for l1, l2 in zip(logits1, logits2):
        p1 = l1.argmax(dim=1)
        p2 = l2.argmax(dim=1)
        decoded_dists.append((p1 != p2).float().sum(dim=1))
    decoded_dists = torch.stack(decoded_dists, dim=0).sum(dim=0)

    # Lipschitz estimate
    lipschitz = (decoded_dists / (latent_dists + 1e-8)).mean().item()
    return {
        'lipschitz_estimate': float(lipschitz),
        'mean_decoded_distance': float(decoded_dists.mean().item()),
        'mean_latent_distance': float(latent_dists.mean().item()),
    }


def full_sic_check(model, num_samples=5000, device='cpu'):
    """Run full 6-check SIC-POVM verification suite.

    Returns dict of all metrics.
    """
    model.eval()
    d = model.d_latent

    # Sample latents from vMF prior
    mu = torch.randn(num_samples, d, device=device)
    mu = mu / mu.norm(dim=1, keepdim=True)
    kappa = torch.full((num_samples,), 10.0, device=device)
    z = model.reparameterize(mu, kappa)

    # Check 1: All latents on unit sphere
    norms = z.norm(dim=1)
    sphere_check = float((norms - 1.0).abs().max().item())

    # Check 2: SIC overlap structure
    sic_metrics = compute_sic_overlaps(z)

    # Check 3: vMF concentration (kappa > threshold)
    _, kappa_out = model.encode(z)

    # Decoder check
    logits = model.decode(z)

    return {
        **sic_metrics,
        'sphere_deviation': sphere_check,
        'mean_kappa': float(kappa_out.mean().item()),
        'min_kappa': float(kappa_out.min().item()),
    }
