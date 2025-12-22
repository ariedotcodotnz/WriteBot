"""
TensorFlow utilities and base models for handwriting synthesis.

This package contains the base model class and various TensorFlow utility functions
used in the RNN implementation.
"""

from .BaseModel import BaseModel
from .utils import *
from .gpu_config import (
    initialize_gpu,
    get_gpu_config,
    is_gpu_available,
    get_device,
    configure_tf_session_for_gpu,
    log_gpu_status,
    GPUConfig,
)
