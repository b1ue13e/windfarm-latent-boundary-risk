"""One explicit numeric execution profile; no scientific parameter changes."""
from __future__ import annotations
import os
import platform
import sys


def configure():
    if 'torch' in sys.modules:
        raise RuntimeError('Configure execution profile before importing torch')
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'
    import torch
    import numpy as np
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    if not torch.cuda.is_available():
        raise RuntimeError('This registered execution profile requires an allocated CUDA GPU')
    return dict(profile='EXTERNAL-DETERMINISTIC-EXECUTION-REPAIR-V1',
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        cudnn_deterministic=torch.backends.cudnn.deterministic,
        cudnn_benchmark=torch.backends.cudnn.benchmark,
        cudnn_tf32=torch.backends.cudnn.allow_tf32,
        matmul_tf32=torch.backends.cuda.matmul.allow_tf32,
        cublas_workspace_config=os.environ.get('CUBLAS_WORKSPACE_CONFIG'),
        torch_threads=torch.get_num_threads(), torch=torch.__version__, cuda=torch.version.cuda,
        numpy=np.__version__, cudnn=torch.backends.cudnn.version(),
        python=sys.version, gpu=torch.cuda.get_device_name(0), host=platform.node(),
        pbs_job_id=os.environ.get('PBS_JOBID'))
