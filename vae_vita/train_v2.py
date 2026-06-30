"""
train_v2.py — VAE-Vita V2 Training Pipeline

Trains the improved 12D hyperspherical VAE (HypersphericalVAEV2) on 
all 17,280,000 crystal configurations with:
- Adaptive SIC regularization (warmup)
- Cosine learning rate schedule
- Gradient clipping + weight decay
- Periodic SIC geometry validation
- Multiple model checkpointing
"""

import os, sys, math, json, time
import torch
import torch.optim as optim
from torch.optim.lr_scheduler import CosineAnnealingLR
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from vae_vita.hyperspherical_vae_v2 import HypersphericalVAEV2, D_LATENT
from vae_vita.crystal_data import CrystalDataset


def validate_model(model, num_samples=10000, device='cpu', use_onehot=False):
    """Evaluate model on random crystal samples."""
    model.eval()
    ds = CrystalDataset(ordinal=not use_onehot, onehot=use_onehot)
    rng = np.random.default_rng(42)
    correct, total = 0, 0
    latents, kappas = [], []
    batch_size = min(1024, num_samples)

    with torch.no_grad():
        for batch_start in range(0, num_samples, batch_size):
            bsize = min(batch_size, num_samples - batch_start)
            indices = rng.integers(0, ds.total, size=bsize)
            if use_onehot:
                x_batch = np.stack([ds.get_onehot(i) for i in indices])
            else:
                x_batch = np.stack([ds.get_ordinal(i) for i in indices])
            x_t = torch.from_numpy(x_batch).float().to(device)
            mu, kappa, z, logits = model(x_t)
            latents.append(z.cpu())
            kappas.append(kappa.cpu())

            for i, (logit, nv) in enumerate(zip(logits, model.value_counts)):
                preds = logit.argmax(dim=-1)
                if use_onehot:
                    offset = sum(model.value_counts[:i])
                    targets = x_t[:, offset:offset+nv].argmax(dim=-1)
                else:
                    targets = (x_t[:, i] * (nv - 1)).long()
                correct += (preds == targets).sum().item()
                total += targets.shape[0]

    z_all = torch.cat(latents, dim=0)
    k_all = torch.cat(kappas, dim=0)
    N = min(10000, len(z_all))
    z_subset = z_all[:N]

    # SIC overlap metrics
    overlaps = torch.mm(z_subset, z_subset.T)
    overlaps_sq = overlaps ** 2
    mask = ~torch.eye(N, dtype=torch.bool, device=z_subset.device)
    off_diag = overlaps_sq[mask]
    mean_overlap = off_diag.mean().item()
    frame_potential = overlaps_sq.mean().item()
    sic_target = 1.0 / 13.0
    sic_deviation = abs(mean_overlap - sic_target)
    
    # Welch bound check
    welch_bound = max(1.0/N, 1.0/13.0)
    welch_satisfied = frame_potential >= welch_bound - 0.01

    # Concentration
    mean_kappa = k_all.mean().item()
    
    # Pairwise overlap histogram (summary)
    overlap_std = off_diag.std().item()

    return {
        'accuracy': correct / max(total, 1),
        'mean_sic_overlap': mean_overlap,
        'frame_potential': frame_potential,
        'sic_deviation': sic_deviation,
        'sic_target': sic_target,
        'welch_satisfied': welch_satisfied,
        'mean_kappa': mean_kappa,
        'overlap_std': overlap_std,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Train VAE-Vita V2")
    parser.add_argument('--steps', type=int, default=50000)
    parser.add_argument('--batch-size', type=int, default=2048)
    parser.add_argument('--lr', type=float, default=3e-4)
    parser.add_argument('--beta', type=float, default=0.3)
    parser.add_argument('--lambda-sic', type=float, default=100.0,
                        help='SIC equiangularity regularization weight (final)')
    parser.add_argument('--warmup', type=int, default=5000,
                        help='Steps for SIC regularization warmup')
    parser.add_argument('--hidden-dim', type=int, default=512)
    parser.add_argument('--n-res-blocks', type=int, default=4)
    parser.add_argument('--use-onehot', action='store_true',
                        help='Use one-hot input encoding')
    parser.add_argument('--checkpoint', type=str, default='vae_vita/vae_vita_v2.pt')
    parser.add_argument('--device', type=str, default='cuda' if torch.cuda.is_available() else 'cpu')
    parser.add_argument('--log-every', type=int, default=200)
    parser.add_argument('--validate-every', type=int, default=1000)
    parser.add_argument('--load', type=str, default=None)
    args = parser.parse_args()

    print("=" * 66)
    print("  VAE-Vita V2: 12D Hyperspherical VAE with Residual Architecture")
    print("=" * 66)
    print(f"  Device:       {args.device}")
    print(f"  Steps:        {args.steps:,}")
    print(f"  Batch size:   {args.batch_size:,}")
    print(f"  LR:           {args.lr}")
    print(f"  Beta (KL):    {args.beta}")
    print(f"  Lambda (SIC): {args.lambda_sic}")
    print(f"  Warmup:       {args.warmup} steps")
    print(f"  Hidden dim:   {args.hidden_dim}")
    print(f"  Res blocks:   {args.n_res_blocks}")
    print(f"  Input:        {'one-hot (49D)' if args.use_onehot else 'ordinal (12D)'}")
    print(f"  Total sees:   {args.steps * args.batch_size:,} / 17,280,000")
    print()

    model = HypersphericalVAEV2(
        d_latent=D_LATENT,
        hidden_dim=args.hidden_dim,
        n_res_blocks=args.n_res_blocks,
        beta=args.beta,
        lambda_sic=args.lambda_sic,
        use_onehot=args.use_onehot,
    ).to(args.device)

    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-5)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.steps, eta_min=args.lr * 0.01)

    start_step = 0
    if args.load:
        ckpt = torch.load(args.load, map_location=args.device)
        model.load_state_dict(ckpt['model_state_dict'])
        optimizer.load_state_dict(ckpt['optimizer_state_dict'])
        if 'scheduler_state_dict' in ckpt:
            scheduler.load_state_dict(ckpt['scheduler_state_dict'])
        start_step = ckpt.get('step', 0)
        print(f"  Resumed from step {start_step}")
        print()

    ds = CrystalDataset(ordinal=not args.use_onehot, onehot=args.use_onehot)
    rng = np.random.default_rng(42)
    best_sic_dev = float('inf')
    best_acc = 0.0
    t_start = time.time()
    step_log = []

    for step in range(start_step, start_step + args.steps):
        model.train()
        indices = rng.integers(0, ds.total, size=args.batch_size)
        if args.use_onehot:
            x_batch = np.stack([ds.get_onehot(i) for i in indices])
        else:
            x_batch = np.stack([ds.get_ordinal(i) for i in indices])
        x_t = torch.from_numpy(x_batch).float().to(args.device)

        optimizer.zero_grad()
        mu, kappa, z, logits = model(x_t)
        total_loss, recon, kl, sic_loss, gram_loss = model.loss(
            x_t, mu, kappa, z, logits,
            step=step, warmup_steps=args.warmup
        )
        total_loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        if (step + 1) % args.log_every == 0:
            elapsed = time.time() - t_start
            sic_w = min(1.0, step / max(1, args.warmup)) * args.lambda_sic
            print(f"  Step {step+1:6d}/{start_step+args.steps} "
                  f"loss={total_loss.item():.2f} "
                  f"recon={recon.item():.2f} "
                  f"kl={kl.item():.3f} "
                  f"sic={sic_loss.item():.6f} "
                  f"lr={scheduler.get_last_lr()[0]:.2e} "
                  f"{elapsed:.0f}s")

        if (step + 1) % args.validate_every == 0:
            metrics = validate_model(model, num_samples=10000, device=args.device,
                                     use_onehot=args.use_onehot)
            elapsed = time.time() - t_start
            print()
            print(f"  ── Validation at step {step+1} ({elapsed:.0f}s) ──")
            print(f"      Accuracy:          {metrics['accuracy']*100:.2f}%")
            print(f"      Mean SIC overlap:  {metrics['mean_sic_overlap']:.6f}  "
                  f"(target: {metrics['sic_target']:.6f})")
            print(f"      Frame potential:   {metrics['frame_potential']:.6f}")
            print(f"      SIC deviation:     {metrics['sic_deviation']:.6f}")
            print(f"      Mean κ:            {metrics['mean_kappa']:.2f}")
            print(f"      Overlap σ:         {metrics['overlap_std']:.6f}")
            print(f"      Welch satisfied:   {metrics['welch_satisfied']}")
            print()

            # Save if best
            improved = metrics['sic_deviation'] < best_sic_dev - 1e-5
            if improved or metrics['accuracy'] > best_acc:
                if improved:
                    best_sic_dev = metrics['sic_deviation']
                if metrics['accuracy'] > best_acc:
                    best_acc = metrics['accuracy']
                ckpt_dir = os.path.dirname(args.checkpoint)
                if ckpt_dir:
                    os.makedirs(ckpt_dir, exist_ok=True)
                torch.save({
                    'step': step + 1,
                    'model_state_dict': model.state_dict(),
                    'optimizer_state_dict': optimizer.state_dict(),
                    'scheduler_state_dict': scheduler.state_dict(),
                    'metrics': metrics,
                }, args.checkpoint)
                tag = "SIC" if improved else "ACC"
                print(f"      ✓ Checkpoint saved ({tag}: dev={best_sic_dev:.6f}, acc={best_acc*100:.1f}%)")
                print()

            step_log.append({
                'step': step + 1,
                **metrics,
                'elapsed': elapsed,
            })

    elapsed = time.time() - t_start
    print("=" * 66)
    print(f"  Training complete ({elapsed:.0f}s)")
    print(f"  Best SIC deviation: {best_sic_dev:.6f}")
    print(f"  Best accuracy:      {best_acc*100:.2f}%")
    print(f"  Target overlap:     1/13 = {1/13:.6f}")
    print()

    print("  Final validation (50K samples)...")
    final = validate_model(model, num_samples=50000, device=args.device,
                           use_onehot=args.use_onehot)
    for k, v in final.items():
        print(f"    {k}: {v}")

    final['elapsed'] = elapsed
    metrics_path = Path(args.checkpoint).with_suffix('.metrics.v2.json')
    with open(metrics_path, 'w') as f:
        json.dump(final, f, indent=2)
    
    # Save full log
    log_path = Path(args.checkpoint).with_suffix('.log.v2.json')
    with open(log_path, 'w') as f:
        json.dump(step_log, f, indent=2)
    
    print(f"  Metrics saved to {metrics_path}")
    print(f"  Model saved to {args.checkpoint}")


if __name__ == '__main__':
    main()
