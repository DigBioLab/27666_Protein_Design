#!/bin/sh
### Day 6 — submit a single-structure RFD3 training run to a GPU node (DTU HPC / LSF).
### Submit from the foundry repo root with:   bsub < submit_train.sh
### Watch it with:   bjobs   /   tail -f day6_train_<job-id>.out

### -- job name --
#BSUB -J day6_rfd3_train
### -- GPU queue: use the GPU queue named in the course materials (e.g. gpuv100 / gpua100) --
#BSUB -q gpuv100
### -- one GPU, exclusive (one job, one GPU — see Day 1 GPU etiquette) --
#BSUB -gpu "num=1:mode=exclusive_process"
### -- 1 host, 4 cores --
#BSUB -n 4
#BSUB -R "span[hosts=1]"
### -- memory per core --
#BSUB -R "rusage[mem=16GB]"
### -- wall-clock limit (hh:mm). Overfitting one structure is quick; 4h is plenty --
#BSUB -W 4:00
### -- stdout / stderr (%J = job-id) --
#BSUB -o day6_train_%J.out
#BSUB -e day6_train_%J.err
### -- email when the job Begins / is Done (uncomment and set your address) --
##BSUB -u your_email@dtu.dk
##BSUB -B
##BSUB -N

# --- activate the course environment (same two lines as Day 1) ---
source /dtu/blackhole/00/c27666/miniforge3/bin/activate
conda activate protein-design

# --- (optional) Weights & Biases: uncomment and set your key to log live curves ---
# export WANDB_API_KEY=...

# --- show the full Python traceback on any Hydra job failure (debugging) ---
export HYDRA_FULL_ERROR=1

# --- paths ---
# Run this script FROM the foundry repo root. DATA is the folder you made in Exercise 4,
# containing both af2_distillation_facebook.parquet and monomer.json. EDIT this path.
DATA="$PWD/single_structure_data"   # foundry repo root holds single_structure_data/
LOGS="$PWD/logs"

# --- launch training ---
# logger=csv writes metrics under $LOGS; swap to logger=wandb if you set WANDB_API_KEY above.
python models/rfd3/src/rfd3/train.py \
    experiment=single_structure \
    paths.data.monomer_distillation_parquet_dir="$DATA" \
    paths.data.monomer_distillation_data_dir="$DATA" \
    paths.data.design_benchmark_data_dir="$DATA" \
    paths.log_dir="$LOGS" \
    logger=csv
