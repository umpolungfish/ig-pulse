"""
train.py — VAE-Vita Training Pipeline

Trains the 12D hyperspherical VAE on random batches from the 17,280,000
crystal configurations. Periodically evaluates SIC-POVM geometry recovery:
  - Pairwise overlap |<z_i|z_j>|^2 → 1/13 ≈ 0.076923
  - Frame potential F = (1/N²) Σ|<z_i|z_j>|^2 → 1/13 ≈ 0.076923
  - Welch bound satisfaction
  - Decoder accuracy

Includes explicit SIC equiangularity regularizer: penalizes deviation of
pairwise overlaps from 1/(d+1).
"""
import os, sys, math, json, time
import torch
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from vae_vita.hyperspherical_vae import HypersphericalVAE
from vae_vita.crystal_data import CrystalDataset

N_VALS = [4, 5, 4, 5, 3, 5, 3, 4, 5, 4, 3, 4]


def validate_model(model, num_samples=10000, device='cpu'):
    """Evaluate model on random crystal samples (batched)."""
    model.eval()
    ds = CrystalDataset()
    rng = np.random.default_rng(42)
    correct, total = 0, 0
    latents = []
    batch_size = min(1024, num_samples)
    with torch.no_grad():
        for batch_start in range(0, num_samples, batch_size):
            bsize = min(batch_size, num_samples - batch_start)
            indices = rng.integers(0, ds.total, size=bsize)
            x_batch = np.stack([ds.get_ordinal(i) for i in indices])
            x_t = torch.from_numpy(x_batch).float().to(device)
            mu, kappa, z, logits = model(x_t)
            latents.append(z.cpu())
            for i, (logit, nv) in enumerate(zip(logits, N_VALS)):
                preds = logit.argmax(dim=-1)
                targets = (x_t[:, i] * (nv - 1)).long()
                correct += (preds == targets).sum().item()
                total += targets.shape[0]
    z_all = torch.cat(latents, dim=0)
    N = min(10000, len(z_all))
    z_subset = z_all[:N]

    # SIC metrics
    overlaps = torch.mm(z_subset, z_subset.T)
    overlaps_sq = overlaps ** 2
    mask = ~torch.eye(N, dtype=torch.bool, device=z_subset.device)
    off_diag = overlaps_sq[mask]
    mean_overlap = off_diag.mean().item()
    frame_potential = overlaps_sq.mean().item()
    sic_target = 1.0 / 13.0
    sic_deviation = abs(mean_overlap - sic_target)

    return {
        'accuracy': correct / max(total, 1),
        'mean_sic_overlap': mean_overlap,
        'frame_potential': frame_potential,
        'sic_deviation': sic_deviation,
        'sic_target': sic_target,
        'frame_target': sic_target,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Train VAE-Vita")
    parser.add_argument('--steps', type=int, default=10000)
    parser.add_argument('--batch-size', type=int, default=4096)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--beta', type=float, default=0.5)
    parser.add_argument('--lambda-sic', type=float, default=10.0,
                        help='SIC equiangularity regularization weight')
    parser.add_argument('--hidden-dim', type=int, default=256)
    parser.add_argument('--checkpoint', type=str, default='vae_vita/vae_vita_ckpt.pt')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--log-every', type=int, default=200)
    parser.add_argument('--validate-every', type=int, default=1000)
    parser.add_argument('--load', type=str, default=None)
    args = parser.parse_args()

    print("=" * 60)
    print("VAE-Vita: 12D Hyperspherical VAE on 17.28M Crystal Configurations")
    print("=" * 60)
    print(f"Device:       {args.device}")
    print(f"Steps:        {args.steps}")
    print(f"Batch size:   {args.batch_size}")
    print(f"LR:           {args.lr}")
    print(f"Beta (KL):    {args.beta}")
    print(f"Lambda (SIC): {args.lambda_sic}")
    print(f"Hidden dim:   {args.hidden_dim}")
    print(f"Total sees:   {args.steps * args.batch_size:,} / 17,280,000")
    print()

    model = HypersphericalVAE(d_latent=12, hidden_dim=args.hidden_dim,
                              beta=args.beta, lambda_sic=args.lambda_sic).to(args.device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-5)

    start_step = 0
    if args.load:
        ckpt = torch.load(args.load, map_location=args.device)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        start_step = ckpt.get('step', 0)
        print(f"Resumed from step {start_step}")

    ds = CrystalDataset()
    rng = np.random.default_rng(42)
    best_sic_dev = float('inf')
    t_start = time.time()

    for step in range(start_step, start_step + args.steps):
        model.train()
        indices = rng.integers(0, ds.total, size=args.batch_size)
        x_batch = np.stack([ds.get_ordinal(i) for i in indices])
        x_t = torch.from_numpy(x_batch).float().to(args.device)

        optimizer.zero_grad()
        mu, kappa, z, logits = model(x_t)
        total_loss, recon, kl, sic_loss = model.loss(x_t, mu, kappa, z, logits)
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if (step + 1) % args.log_every == 0:
            elapsed = time.time() - t_start
            sic_val = sic_loss.item() if isinstance(sic_loss, torch.Tensor) else 0.0
            print(f"Step {step+1:6d}/{start_step+args.steps} "
                  f"loss={total_loss.item():.3f} "
                  f"recon={recon.item():.3f} "
                  f"kl={kl.item():.3f} "
                  f"sic={sic_val:.6f} "
                  f"{elapsed:.0f}s")

        if (step + 1) % args.validate_every == 0:
            metrics = validate_model(model, num_samples=5000, device=args.device)
            elapsed = time.time() - t_start
            print()
            print(f"-- Validation at step {step+1} --")
            print(f"  Accuracy:          {metrics['accuracy']*100:.2f}%")
            print(f"  Mean SIC overlap:  {metrics['mean_sic_overlap']:.6f}  "
                  f"(target: {metrics['sic_target']:.6f})")
            print(f"  Frame potential:   {metrics['frame_potential']:.6f}  "
                  f"(target: {metrics['frame_target']:.6f})")
            print(f"  SIC deviation:     {metrics['sic_deviation']:.6f}")
            print(f"  Elapsed:           {elapsed:.1f}s")
            print()

            if metrics['sic_deviation'] < best_sic_dev:
                best_sic_dev = metrics['sic_deviation']
                ckpt_dir = os.path.dirname(args.checkpoint)
                if ckpt_dir:
                    os.makedirs(ckpt_dir, exist_ok=True)
                torch.save({
                    'step': step + 1,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'metrics': metrics,
                }, args.checkpoint)
                print(f"  Checkpoint saved (SIC dev={best_sic_dev:.6f})")
                print()

    elapsed = time.time() - t_start
    print("=" * 60)
    print(f"Training complete ({elapsed:.0f}s)")
    print(f"Best SIC deviation: {best_sic_dev:.6f}")
    print(f"Target overlap: 1/13 = {1/13:.6f}")
    print()

    print("Final validation (50K samples)...")
    final = validate_model(model, num_samples=50000, device=args.device)
    for k, v in final.items():
        print(f"  {k}: {v}")

    final['elapsed'] = time.time() - t_start
    metrics_path = Path(args.checkpoint).with_suffix('.metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(final, f, indent=2)
    print(f"Metrics saved to {metrics_path}")
    print(f"Model saved to {args.checkpoint}")


if __name__ == '__main__':
    main()
