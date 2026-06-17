# Binder Design Pipeline — Course 27666

A teaching pipeline for *de novo* protein binder design on the DTU GPU cluster:

```
RFD3 (backbones)  →  ProteinMPNN (sequences)  →  RF3 (fold & score)
```

The worked example designs binders against the **MMP9** catalytic domain. Everything
needed is bundled in this repo; the heavy models and their conda environments live in the
shared, read-only `/dtu/projects/dbl/...` tree, so you don't install anything large.

All GPU jobs run through the **`c27666`** LSF queue.

---

## 1. Get the repo into your own scratch space

Each student works in their **own** `/work3/<username>` — nothing is shared-writable.

```bash
cd /work3/$USER
git clone <REPO-URL> binder-design-course
cd binder-design-course
```

Run outputs are written under `work/<experiment>/` inside your clone (git-ignored), so your
designs never collide with anyone else's.

## 2. Pick a Jupyter kernel

The notebook itself only needs basic scientific Python (`numpy`, `pandas`, `matplotlib`) —
the models run in their own envs inside the batch jobs, not in the kernel. Register any env
that has those packages once, e.g. the shared base:

```bash
source /dtu/projects/dbl/foundry/miniforge3/etc/profile.d/conda.sh
conda activate base                      # or your own env with numpy/pandas/matplotlib
python -m ipykernel install --user --name binder_design --display-name "binder_design"
```

Open `Binder_design_course.ipynb` and select **Kernel → binder_design**.

## 3. Run it

Run cells top to bottom. The three GPU stages **do not run inside the notebook** — each cell
writes an LSF submit script and prints a `bsub < ...` command. The loop for every stage is:

1. Run the notebook cell → it writes a submit script.
2. In a terminal: `bsub < work/exp_01/submit/<stage>.sh`
3. Wait for the job to finish: `bstat` (job disappears when done). Logs land in
   `work/exp_01/logs/`.
4. Run the next "process / score" cell, then move to the next stage.

Stage order: **RFD3 → process → MPNN → RF3 (build JSONs → submit) → score → collect best**.

---

## Queue notes (`c27666`)

- Shared by the whole class on **only a couple of GPUs** (`exclusive_process` → one job per
  GPU). Keep design counts **small** — the notebook defaults are deliberately tiny
  (4 backbones × 2 sequences). Scale up only when the queue is idle (`bqueues c27666`).
- **Wall time:** max 12 h; the queue *default is 15 min*, so the submit scripts always set
  `-W 12:00`. Never submit GPU work without `-W`.
- Monitor: `bstat` / `bjobs`. Kill a job: `bkill <jobid>`.

## Repo layout

```
binder-design-course/
├── Binder_design_course.ipynb   # the pipeline
├── README.md
├── lib/
│   ├── jupyter_utils.py          # builds LSF array submit scripts (c27666, GPU-aware)
│   └── rf3_metrics.py            # parses RF3 .score files → confidence metrics
├── inputs/
│   ├── target_rfd3.pdb           # RFD3 diffusion target (MMP9)
│   ├── MMP9_target.cif           # RF3 folding target (MMP9 + Zn/Ca)
│   └── rf3_template.json         # RF3 input template (binder chain A + target + cofactors)
└── work/                         # created at runtime, git-ignored
    └── <experiment>/{cmds,submit,logs,configs,scores,
                       diffusion_out,mpnn_out,rf3_out,best_binders}
```

## Using your own target

Replace the files in `inputs/`, then in the notebook adjust: the RFD3 `contig` /
`select_hotspots` (Stage 1), and the RF3 chain IDs in the scoring cell (`A_1` = binder,
`B_1` = target). The cofactor `ccd_code` entries in `rf3_template.json` should match your
target's metals/ligands.
