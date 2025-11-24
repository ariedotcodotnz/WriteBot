"""
Configuration module for the handwriting synthesis package.

This module defines paths for data, checkpoints, predictions, and styles
used by the handwriting synthesis model. It automatically resolves paths
relative to the project root.
"""

import os

# Get the directory containing this config file (handwriting_synthesis/)
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (one level up from handwriting_synthesis/)
_PROJECT_ROOT = os.path.dirname(_CONFIG_DIR)

BASE_PATH = os.path.join(_PROJECT_ROOT, "model")
BASE_DATA_PATH = "data"

data_path: str = os.path.join(BASE_PATH, BASE_DATA_PATH)
"""Path to the data directory."""

processed_data_path: str = os.path.join(data_path, "processed")
"""Path to the processed data directory."""

raw_data_path: str = os.path.join(data_path, "raw")
"""Path to the raw data directory."""

ascii_data_path: str = os.path.join(raw_data_path, "ascii")
"""Path to the ASCII data directory."""

checkpoint_path: str = os.path.join(BASE_PATH, "checkpoint")
"""Path to the model checkpoint directory."""

prediction_path: str = os.path.join(BASE_PATH, "prediction")
"""Path to the prediction output directory."""

style_path: str = os.path.join(BASE_PATH, "style")
"""Path to the style samples directory."""
