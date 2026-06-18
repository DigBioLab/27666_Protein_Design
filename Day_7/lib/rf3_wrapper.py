"""
rf3_wrapper.py — run rf3 with a pynvml patch for A100 MIG GPU slices.

On MIG slices, pynvml.nvmlDeviceGetNumGpuCores raises NVMLError_NotSupported.
cuequivariance_ops calls this unconditionally at import time and crashes.
This wrapper patches the function BEFORE modelhub (and hence cuequivariance_ops)
is imported, so the patch is in effect for the entire process.

Usage (replace bare `rf3` calls):
    python /path/to/lib/rf3_wrapper.py fold inference_engine=rf3 inputs=... ...
"""
import pynvml as _pynvml

_orig_get_cores = _pynvml.nvmlDeviceGetNumGpuCores


def _safe_get_cores(handle):
    try:
        return _orig_get_cores(handle)
    except _pynvml.NVMLError_NotSupported:
        # MIG slices do not expose core count; return a plausible fallback.
        # The value is only used for a triton cache key, so accuracy does not
        # affect model correctness — it just needs to be consistent.
        return 6912  # A100 SXM total CUDA cores; safe constant for MIG slices


_pynvml.nvmlDeviceGetNumGpuCores = _safe_get_cores

# Entry point: modelhub.cli:app (same as the `rf3` console script)
from modelhub.cli import app  # noqa: E402

app()
