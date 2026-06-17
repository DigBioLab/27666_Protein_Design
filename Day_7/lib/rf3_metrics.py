"""
rf3_metrics.py — parse RF3 .score files and aggregate per-design confidence metrics.

RF3 .score files are CSVs with two types of rows mixed together:
  - Chain rows:     have 'chain_chainwise' populated
  - Interface rows: have 'chain_i_interface' / 'chain_j_interface' populated

Key metrics extracted:
  best_binder_plddt   — chainwise pLDDT of the binder at the best-model batch_idx
  AF_best_min_pae     — min interface PAE (binder ↔ target_f) at best batch_idx [Å, lower=better]
  AF_ipsae_at_best    — interface ipSAE (binder ↔ target_f) at best batch_idx [0-1, higher=better]

ipSAE is a pTM-like score (0-1, higher = better interface confidence).
Using ipsae_interface (chain-pair specific) NOT overall_ipsae (which is max across ALL pairs
including metal ions ZN/CA, making it inflated and uninformative for binder quality).
"""

import glob
import pandas as pd
from pathlib import Path


def _interface_matches(row, chain_a, chain_b):
    """True if this interface row is between chain_a and chain_b (in either order)."""
    ci = str(row.get("chain_i_interface", ""))
    cj = str(row.get("chain_j_interface", ""))
    return (ci == chain_a and cj == chain_b) or (ci == chain_b and cj == chain_a)


def gather_rf3_metrics(parent, binder, target_f, target_g, out_csv=None):
    """Parse all RF3 .score files under `parent` and compile per-design metrics.

    Args:
        parent:   Directory containing RF3 output .score files (searched recursively)
        binder:   Chain ID for the binder, e.g. "A_1"
        target_f: Chain ID for target F (primary target), e.g. "B_1"
        target_g: Chain ID for target G (secondary target), e.g. "B_1"
        out_csv:  Optional path to write the aggregated CSV

    Returns:
        pd.DataFrame with one row per design
    """
    score_files = sorted(Path(parent).rglob("*.score"))

    records = []
    for sf in score_files:
        try:
            raw = pd.read_csv(sf)
        except Exception:
            continue

        if raw.empty or "chain_chainwise" not in raw.columns:
            continue

        # Split into chain-level rows and interface-level rows
        chain_df = raw[raw["chain_chainwise"].notna()].copy()
        iface_df = raw[raw["chain_chainwise"].isna()].copy()

        if chain_df.empty or iface_df.empty:
            continue

        # --- Find AF interface rows (binder ↔ target_f) ---
        af_mask = iface_df.apply(lambda r: _interface_matches(r, binder, target_f), axis=1)
        af_iface = iface_df[af_mask].copy()
        if af_iface.empty:
            continue

        # --- Find AG interface rows (binder ↔ target_g) ---
        ag_mask = iface_df.apply(lambda r: _interface_matches(r, binder, target_g), axis=1)
        ag_iface = iface_df[ag_mask].copy()

        # --- Pick best batch_idx = lowest min_pae_interface for the AF interface ---
        best_idx_row = af_iface.loc[af_iface["min_pae_interface"].idxmin()]
        best_batch = best_idx_row["batch_idx"]

        # --- Extract metrics at best batch_idx ---
        binder_rows = chain_df[
            (chain_df["chain_chainwise"] == binder) &
            (chain_df["batch_idx"] == best_batch)
        ]
        af_best = af_iface[af_iface["batch_idx"] == best_batch]
        ag_best = ag_iface[ag_iface["batch_idx"] == best_batch] if not ag_iface.empty else pd.DataFrame()

        best_binder_plddt = float(binder_rows["chainwise_plddt"].values[0]) if len(binder_rows) else float("nan")
        af_min_pae        = float(af_best["min_pae_interface"].values[0])    if len(af_best) else float("nan")

        # ipSAE: pTM-like score (0-1, higher = better interface confidence)
        af_ipsae_at_best  = float(af_best["ipsae_interface"].values[0])      if len(af_best) else float("nan")

        ag_min_pae        = float(ag_best["min_pae_interface"].values[0])    if len(ag_best) else float("nan")
        ag_ipsae_at_best  = float(ag_best["ipsae_interface"].values[0])      if len(ag_best) else float("nan")

        records.append({
            "design_id":          sf.stem,
            "score_file":         str(sf),
            "best_binder_plddt":  best_binder_plddt,
            "AF_best_min_pae":    af_min_pae,
            "AF_ipsae_at_best":   af_ipsae_at_best,
            "AG_best_min_pae":    ag_min_pae,
            "AG_ipsae_at_best":   ag_ipsae_at_best,
            "best_batch_idx":     int(best_batch),
        })

    df = pd.DataFrame(records)

    if out_csv and not df.empty:
        Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv, index=False)
        print(f"Wrote {len(df)} records → {out_csv}")

    return df
