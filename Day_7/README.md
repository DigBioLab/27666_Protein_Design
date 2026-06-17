# Binder Design Pipeline — Course 27666

A teaching pipeline for *de novo* protein binder design on the DTU GPU cluster:

```
RFD3 (backbones)  →  ProteinMPNN (sequences)  →  RF3 (fold & score)
```

You point the pipeline at **any target protein**: give it a target structure and a few
hotspot residues, and it designs binder backbones, threads sequences onto them, and folds
each binder–target complex to score the interface. An example target is bundled in
`inputs/` so the notebook runs out of the box — swap it for your own (see
*Using your own target*).

Everything needed is in this folder; the heavy models and their conda environments live in
the shared, read-only `/dtu/projects/dbl/...` tree, so you don't install anything large.
All GPU jobs run through the **`c27666`** LSF queue.

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
python -m ipykernel install --user --name binder_design --display-name "binder_design"
```

Open `Binder_design_course.ipynb` (from inside `Day_7/`) and select
**Kernel → binder_design**.

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

Stage order: **RFD3 → process → MPNN → RF3 (build JSONs → submit) → score → collect best**.

---

## Queue notes (`c27666`)

- Shared by the whole class on **only a couple of GPUs**, which are **MIG-partitioned into
  ~20 GB slices** (one job per slice). Keep designs **small** — the notebook defaults are
  deliberately tiny (a few backbones × a few sequences), and you should keep the target
  context modest so it fits in 20 GB. Scale up only when the queue is idle (`bqueues c27666`).
- **Wall time:** max 12 h, but the queue *default is only 15 min*, so every submit script
  sets `-W` explicitly. **Never submit GPU work without `-W`** or it is killed at 15 min. If
  you raise the design counts, raise the matching `-W` too.
- Monitor: `bstat` / `bjobs`. Kill a job: `bkill <jobid>`.

## Repo layout

```
Day_7/
├── Binder_design_course.ipynb   # the pipeline
├── README.md
├── lib/
│   ├── jupyter_utils.py          # builds LSF array submit scripts (c27666, GPU-aware)
│   └── rf3_metrics.py            # parses RF3 .score files → confidence metrics
├── inputs/
│   ├── <target>.pdb              # RFD3 diffusion target (the structure to design against)
│   ├── <target>.cif              # RF3 folding target
│   └── rf3_template.json         # RF3 input template (binder chain A + target [+ cofactors])
└── work/                         # created at runtime
    └── <experiment>/{cmds,submit,logs,configs,scores,
                       diffusion_out,mpnn_out,rf3_out,best_binders}
```

## Using your own target

The pipeline is target-agnostic. To design against your own protein:

1. **Put your structures in `inputs/`** — a PDB for RFD3 and a CIF for RF3 (same target).
2. **RFD3 cell (Stage 1):** set `input_pdb` to your PDB, and choose:
   - `contig` — binder length + which target residues/chains to keep (e.g. `50-150,/0,A40-180`).
   - `select_hotspots` — the target residues (and atoms) the binder should engage.
   - `length` — total design length; **must match the contig** (binder + kept target residues).
3. **RF3 template (`inputs/rf3_template.json`):** point its target `path` at your CIF and set
   `template_selection` to the target chain. Keep the binder component as chain `A`. If your
   target has metals/ligands, add matching `ccd_code` entries (a single-domain protein with
   none needs no cofactors).
4. **Scoring cell:** chain IDs in RF3 output are `A_1` = binder, `B_1` = target — adjust only
   if your template differs.

Keep the kept-target context small enough to fit the 20 GB GPU slice (trim `contig` to a
window around your hotspots if RFD3 runs out of memory).
