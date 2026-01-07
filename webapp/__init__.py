"""Webapp package init for imports in tests."""

# CRITICAL: Set Keras 2 legacy mode BEFORE any TensorFlow imports
# TensorFlow 2.16+ defaults to Keras 3 which breaks TF1 compat code
import os
os.environ.setdefault('TF_USE_LEGACY_KERAS', '1')
