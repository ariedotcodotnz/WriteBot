"""
Handwriting Synthesis Package.

This package contains the core components for the handwriting synthesis model,
including the RNN model, drawing operations, and training utilities.
"""

# CRITICAL: Set Keras 2 legacy mode BEFORE any TensorFlow imports
# TensorFlow 2.16+ defaults to Keras 3 which breaks TF1 compat code
import os
os.environ.setdefault('TF_USE_LEGACY_KERAS', '1')

# from .data_frame import *
# from .drawing import *
from .hand import Hand
# from .rnn import *
# from .tf import *
# from .training import *
