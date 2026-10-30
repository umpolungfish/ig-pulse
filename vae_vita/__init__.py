"""
vae_vita — 12D Hyperspherical VAE on the 17.28M Crystal of Types

The VAE-Vita independently recovers the d=12 SIC-POVM geometry by learning
to encode/decode all 17,280,000 structural types of the Imscribing Grammar.
"""

from .hyperspherical_vae import HypersphericalVAE, D_LATENT, D_INPUT
from .crystal_data import CrystalDataset
from .verify_sic import full_sic_check, compute_sic_overlaps
