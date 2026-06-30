#!/usr/bin/env python3
"""Self-contained VAE-Vita V2 training script."""
import sys, os, time, json, math
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

# ── Model definition ────────────────────────────────────────────────
D_LATENT = 12
KAPPA_MIN, KAPPA_MAX = 0.1, 100.0

def _bessel_ratio(d, kappa):
    kappa_safe = torch.clamp(kappa.abs(), min=1e-6)
    a = torch.full_like(kappa_safe, float(d))
    b = 2 * kappa_safe
    tiny = 1e-30
    f = tiny; C = f; D = torch.zeros_like(kappa_safe)
    for j in range(200):
        Db = b + a * D; Db = torch.where(Db.abs() < tiny, torch.full_like(Db, tiny), Db)
        C = b + a / C; C = torch.where(C.abs() < tiny, torch.full_like(C, tiny), C)
        D = 1.0 / Db; delta = C * D; f = f * delta
        if delta.abs().max().item() < 1e-12 and j > 5: break
        a = a + 2.0
    return f

def _log_vmf_constant(d, kappa):
    d_half = d//2; ks = torch.clamp(kappa, min=1e-6, max=KAPPA_MAX)
    ratio = _bessel_ratio(d, ks)
    return (d_half-1)*torch.log(ks) - d_half*math.log(2*math.pi) - torch.log(ratio.clamp(min=1e-30))

def _kl_vmf_uniform(mu, kappa, d=12):
    log_C = _log_vmf_constant(d, kappa)
    log_area_S = math.log(2) + (d/2)*math.log(math.pi) - math.lgamma(d/2)
    ratio = _bessel_ratio(d, kappa)
    return (kappa * ratio + log_C + log_area_S).clamp(min=0.0)

def _vmf_reparameterize(mu, kappa, d=12):
    bs = mu.shape[0]; dev = mu.device; ks = torch.clamp(kappa, min=KAPPA_MIN, max=KAPPA_MAX)
    ba = float((d-1)/2); bb = float((d-1)/2)
    b = (-2*ks + torch.sqrt(4*ks**2 + (d-1)**2)) / (d-1)
    x0 = (1-b)/(1+b); c = ks*x0 + (d-1)*torch.log(1-x0**2)
    beta_d = torch.distributions.Beta(torch.tensor(ba,device=dev), torch.tensor(bb,device=dev))
    w_samples = []
    for _ in range(10):
        z_b = beta_d.sample((bs,))
        wa = (1-(1+b)*z_b)/(1-(1-b)*z_b)
        la = ks*wa + (d-1)*torch.log(1-wa**2+1e-30) - c
        mask = torch.log(torch.rand(bs,device=dev)+1e-30) <= la
        w_samples.append(wa * mask.float())
    w = torch.stack(w_samples, dim=0).max(dim=0)[0].clamp(-1+1e-7, 1-1e-7)
    vf = F.normalize(torch.randn(bs, d-1, device=dev), dim=1)
    st = torch.sqrt((1-w**2).clamp(min=0.0))
    z_e1 = torch.cat([w.unsqueeze(1), st.unsqueeze(1)*vf], dim=1)
    mu_u = F.normalize(mu, dim=1)
    e1 = torch.zeros(bs, d, device=dev); e1[:,0] = 1.0
    u = F.normalize(e1 - mu_u, dim=1)
    return z_e1 - 2*(z_e1*u).sum(dim=1,keepdim=True)*u

def sic_loss_fn(z, target=1.0/13.0):
    N = z.shape[0]
    o = torch.mm(z, z.T)**2
    m = ~torch.eye(N, dtype=torch.bool, device=z.device)
    return F.mse_loss(o[m], torch.full_like(o[m], target))

class ResBlock(nn.Module):
    def __init__(self, dim, dp=0.1):
        super().__init__()
        self.net = nn.Sequential(nn.LayerNorm(dim), nn.Linear(dim,dim), nn.GELU(), nn.Dropout(dp), nn.LayerNorm(dim), nn.Linear(dim,dim))
    def forward(self, x): return x + self.net(x)

class HypersphericalVAEV2(nn.Module):
    def __init__(self, d_latent=12, hdim=384, nrb=3, beta=0.3, ls=200.0):
        super().__init__()
        self.d_latent=d_latent; self.beta=beta; self.lambda_sic=ls
        self.vc = [4,5,4,5,3,5,3,4,5,4,3,4]
        self.ip = nn.Linear(12, hdim)
        self.eb = nn.Sequential(*[ResBlock(hdim) for _ in range(nrb)])
        self.mh = nn.Sequential(nn.LayerNorm(hdim), nn.Linear(hdim, d_latent))
        self.kh = nn.Sequential(nn.LayerNorm(hdim), nn.Linear(hdim,1), nn.Softplus())
        self.lp = nn.Linear(d_latent, hdim)
        self.db = nn.Sequential(*[ResBlock(hdim) for _ in range(nrb)])
        self.oh = nn.ModuleList([nn.Sequential(nn.LayerNorm(hdim), nn.Linear(hdim,hdim//2), nn.GELU(), nn.Linear(hdim//2,nv)) for nv in self.vc])
        self.apply(lambda m: [nn.init.xavier_uniform_(m.weight,gain=0.5) for _ in [0] if isinstance(m,nn.Linear)])

    def encode(self, x):
        h = self.eb(self.ip(x))
        return F.normalize(self.mh(h), dim=1), torch.clamp(self.kh(h).squeeze(-1)+2.0, min=KAPPA_MIN, max=KAPPA_MAX)

    def decode(self, z): return [h(self.db(self.lp(z))) for h in self.oh]

    def forward(self, x):
        mu,k = self.encode(x); z = _vmf_reparameterize(mu,k)
        return mu, k, z, self.decode(z)

    def loss(self, x, mu, kappa, z, logits, step=0, ws=5000):
        rl = sum(F.cross_entropy(l, (x[:,i]*(nv-1)).long(), reduction='mean')
                for i,(l,nv) in enumerate(zip(logits,self.vc)))
        kl = _kl_vmf_uniform(mu, kappa, self.d_latent).mean()
        sw = min(1.0, step/max(1,ws)) * self.lambda_sic
        sl = sic_loss_fn(z) if sw > 0 else torch.tensor(0.0, device=z.device)
        return rl + self.beta*kl + sw*sl, rl, kl, sl

# ── Training ─────────────────────────────────────────────────────────
device = 'cuda'
model = HypersphericalVAEV2(d_latent=12, hdim=384, nrb=3, beta=0.3, ls=200.0).to(device)
opt = torch.optim.AdamW(model.parameters(), lr=5e-4, weight_decay=1e-5)
sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=30000, eta_min=5e-6)

# Crystal data
VC = [4,5,4,5,3,5,3,4,5,4,3,4]
N_VALS = np.cumsum([1] + VC)

def sample(batch_size):
    idx = np.random.randint(0, 17280000, size=batch_size)
    x = np.zeros((batch_size, 12), dtype=np.float32)
    for i, idx_i in enumerate(idx):
        r = idx_i
        for j, nv in enumerate(VC):
            x[i,j] = (r % nv) / (nv-1)
            r //= nv
    return torch.from_numpy(x).float().to(device)

def validate(n=10000):
    model.eval()
    with torch.no_grad():
        x = sample(n); mu,k,z,logits = model(x)
        N = min(5000, len(z)); zs = z[:N]
        o = (torch.mm(zs,zs.T)**2)
        m = ~torch.eye(N,dtype=torch.bool,device=device)
        od = o[m]
        mo = od.mean().item(); sd = abs(mo-1/13)
        cor,tot = 0,0
        for i,(l,nv) in enumerate(zip(logits,VC)):
            cor += (l.argmax(dim=-1) == (x[:,i]*(nv-1)).long()).sum().item()
            tot += x.shape[0]
        return {'acc': cor/tot, 'mo': mo, 'sd': sd, 'mk': k.mean().item()}

t0 = time.time(); best = float('inf')
for step in range(30000):
    model.train(); opt.zero_grad()
    x = sample(2048)
    mu,k,z,logits = model(x)
    tl,rl,kl,sl = model.loss(x,mu,k,z,logits,step=step,ws=5000)
    tl.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
    opt.step(); sch.step()
    if (step+1)%200==0:
        print(f'Step {step+1:6d}: loss={tl.item():.2f} recon={rl.item():.2f} kl={kl.item():.3f} sic={sl.item():.6f} lr={sch.get_last_lr()[0]:.2e} [{time.time()-t0:.0f}s]', flush=True)
    if (step+1)%1000==0:
        m = validate()
        print(f'  ── Val @ {step+1} ({time.time()-t0:.0f}s) ── Acc: {m["acc"]*100:.2f}%  SIC ov: {m["mo"]:.6f}  Dev: {m["sd"]:.6f}  κ: {m["mk"]:.2f}', flush=True)
        if m['sd'] < best:
            best = m['sd']
            torch.save({'step':step+1,'model':model.state_dict(),'metrics':m}, 'vae_vita/vae_vita_v2.pt')
            print(f'    ✓ Saved (SIC dev={best:.6f})', flush=True)

print(f'\nDone! Best SIC dev: {best:.6f}', flush=True)
