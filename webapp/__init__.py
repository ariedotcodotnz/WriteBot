"""Webapp package init for imports in tests."""

# CRITICAL: Set Keras 2 legacy mode BEFORE any TensorFlow imports
# TensorFlow 2.16+ defaults to Keras 3 which breaks TF1 compat code
import os
os.environ['TF_USE_LEGACY_KERAS'] = '1'

# Pre-import tf_keras to avoid lazy loader recursion in TF 2.18+
try:
    import tf_keras  # noqa: F401
except ImportError:
    pass
