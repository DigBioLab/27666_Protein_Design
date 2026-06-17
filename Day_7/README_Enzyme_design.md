# Enzyme Design Pipeline — Course 27666

A teaching pipeline for *de novo* enzyme design on the DTU GPU cluster:

```
RFD3 (backbones)  →  LigandMPNN (sequences)  →  RF3 (fold & score)
```

You start from a **theozyme** — a catalytic motif (here a Ser–Asp–His triad) positioned
around a substrate — and design a whole enzyme scaffold around it: RFD3 builds backbones
that hold the catalytic geometry, LigandMPNN designs sequences conditioned on the substrate
(keeping the catalytic residues fixed), and RF3 folds each enzyme + substrate complex to
score the fold and the substrate pocket. A worked example (a **serine hydrolase** around a
**PET-monomer-mimic substrate**, theozyme `5XH3`) is bundled in `inputs/` so the notebook
runs out of the box — swap it for your own (see *Using your own theozyme*).

This pipeline shares its infrastructure with the binder-design notebook in this folder
(`Binder_design_course.ipynb`): the same `lib/` helpers, the same `inputs/` folder, and the
same `c27666` LSF queue. The heavy models and their conda environments live in the shared,
read-only `/dtu/projects/dbl/...` tree, so you don't install anything large.

---

## 1. Get the repo into your own scratch space

Each student works in their **own** `/work3/<username>` — nothing is shared-writable.

```bash
cd /work3/$USER
git clone https://github.com/DigBioLab/27666_Protein_Design.git
cd 27666_Protein_Design/Day_7
```

Run outputs are written under `work/<experiment>/` inside `Day_7`, separate from the repo
files, so your designs never collide with anyone else's.

## 2. Pick a Jupyter kernel

The notebook itself only needs basic scientific Python (`numpy`, `pandas`, `matplotlib`) —
the models run in their own envs inside the batch jobs, not in the kernel. Register any env
that has those packages once, e.g. the shared base:

```bash
source /dtu/projects/dbl/foundry/miniforge3/etc/profile.d/conda.sh
conda activate base                      # or your own env with numpy/pandas/matplotlib
python -m ipykernel install --user --name enzdes --display-name "enzdes"
```

Open `Enzyme_design_course.ipynb` (from inside `Day_7/`) and select **Kernel → enzdes**.

## 3. Run it

Run cells top to bottom. The three GPU stages **do not run inside the notebook** — each cell
writes an LSF submit script and prints the exact `bsub < ...` command to run. The loop for
every stage is:

1. Run the notebook cell → it writes a submit script and prints a `bsub < ...` line.
2. Copy that printed line into a terminal and run it. (Always use the path the cell prints —
   submit scripts live under `work/<experiment>/submit/` or `.../cmds/` depending on stage.)
3. Wait for the job to finish: `bstat` (the job disappears when done). Logs land under
   `work/<experiment>/logs/` (or `cmds/logs/` for MPNN).
4. Run the next "process / score" cell, then move to the next stage.

Stage order: **RFD3 → process/filter → LigandMPNN → RF3 (build JSONs → submit) → score →
collect best**.

---

## Queue notes (`c27666`)

- Shared by the whole class on **only a couple of GPUs**, which are **MIG-partitioned into
  ~20 GB slices** (one job per slice). Keep designs **small** — the notebook defaults are
  deliberately tiny (a couple of backbones × a couple of sequences). Scale up only when the
  queue is idle (`bqueues c27666`).
- **Wall time:** max 12 h, but the queue *default is only 15 min*, so every submit script
  sets `-W` explicitly. **Never submit GPU work without `-W`** or it is killed at 15 min. If
  you raise the design counts, raise the matching `-W` too.
- Monitor: `bstat` / `bjobs`. Kill a job: `bkill <jobid>`.

## Repo layout

```
Day_7/
├── Enzyme_design_course.ipynb    # this pipeline
├── Binder_design_course.ipynb    # sibling binder pipeline (shares lib/ and inputs/)
├── README_Enzyme_design.md
├── lib/
│   ├── jupyter_utils.py          # builds LSF array submit scripts (c27666, GPU-aware)
│   └── rf3_metrics.py            # parses RF3 .score files → confidence metrics
├── inputs/
│   └── 5XH3.pdb                  # theozyme: scaffold residues + catalytic triad + ligand pt1
└── work/                         # created at runtime
    └── <experiment>/{cmds,submit,logs,configs,scores,
                       diffusion_out,mpnn_out,rf3_out,best_designs}
```

## How the enzyme pipeline differs from binder design

Same three stages and queue, but:

- **RFD3** holds the **catalytic residues** fixed (`select_fixed_atoms`, `select_catres`) and
  builds the scaffold around the **substrate ligand** — there are no hotspots, and
  `infer_ori_strategy` is `None`.
- **LigandMPNN** (not plain ProteinMPNN) designs sequences **conditioned on the ligand** and
  keeps the catalytic residues fixed. Each backbone's `diffused_index_map` (written by RFD3)
  maps the catalytic residues to their position in the designed numbering for `--fixed_residues`.
- **RF3** folds the enzyme **with the substrate supplied as chemistry** (a SMILES string for a
  non-CCD ligand, or a CCD code). Scoring reads the same `.score` files as the binder pipeline,
  but the relevant "interface" is **enzyme (`A_1`) ↔ substrate (`B_1`)**, so the metrics report
  the enzyme fold confidence and how confidently RF3 docks the ligand in the pocket.

## Using your own theozyme

The pipeline is theozyme-agnostic. To design your own enzyme:

1. **Put your theozyme PDB in `inputs/`** — the scaffold/motif residues plus the substrate as
   a `HETATM` ligand with a residue name (e.g. `pt1`).
2. **RFD3 cell (Stage 1):** set `input_pdb`, and choose:
   - `contig` — free ranges to design + fixed motif residues to copy (e.g.
     `30-50,A131-132,20-40,A177-177,...`).
   - `catres` — the catalytic residues to keep (and not redesign).
   - `fixed_atoms` — the sidechain atoms to pin per catalytic residue.
   - `ligand_name` — the substrate residue name in your PDB.
   - `length` — total design length range; must be consistent with the contig.
3. **RF3 cell (Stage 3):** set the substrate chemistry — `smiles_str` for a non-CCD ligand,
   or `ccd_ligand=True` with a `ligand_code` for a standard CCD ligand.
4. **Scoring cell:** chain IDs in RF3 output are `A_1` = enzyme, `B_1` = substrate — adjust
   only if your inputs differ. Tune `PLDDT_CUT` / `PAE_CUT` / `IPSAE_CUT` to your standards.

Keep the design length modest enough to fit the 20 GB GPU slice.
