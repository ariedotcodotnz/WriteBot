"""
GPU configuration and detection utilities for TensorFlow.

This module provides automatic GPU detection and configuration with CPU fallback.
Optimized for NVIDIA RTX 50 series (Blackwell architecture) GPUs.
"""

import os
import logging
import warnings
from typing import Optional, Dict, Any, List, Tuple

# Suppress TensorFlow warnings before import
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '2')
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='tensorflow')

import tensorflow as tf

logger = logging.getLogger(__name__)


class GPUConfig:
    """GPU configuration manager with automatic detection and fallback."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if GPUConfig._initialized:
            return

        self._gpu_available = False
        self._gpu_devices = []
        self._gpu_info = {}
        self._memory_growth_enabled = False
        self._mixed_precision_enabled = False

        self._detect_and_configure()
        GPUConfig._initialized = True

    def _detect_and_configure(self) -> None:
        """Detect available GPUs and configure TensorFlow accordingly."""
        try:
            # Get list of physical GPUs
            physical_gpus = tf.config.list_physical_devices('GPU')

            if physical_gpus:
                self._gpu_available = True
                self._gpu_devices = physical_gpus

                for gpu in physical_gpus:
                    # Enable memory growth to prevent TF from allocating all GPU memory
                    try:
                        tf.config.experimental.set_memory_growth(gpu, True)
                        self._memory_growth_enabled = True
                    except RuntimeError as e:
                        # Memory growth must be set before GPUs are initialized
                        logger.warning(f"Could not set memory growth: {e}")

                    # Get GPU details
                    gpu_details = tf.config.experimental.get_device_details(gpu)
                    self._gpu_info[gpu.name] = gpu_details

                # Log GPU information
                logger.info(f"GPU(s) detected: {len(physical_gpus)}")
                for gpu in physical_gpus:
                    details = self._gpu_info.get(gpu.name, {})
                    compute_cap = details.get('compute_capability', 'unknown')
                    logger.info(f"  - {gpu.name}: compute capability {compute_cap}")

                # Check for RTX 50 series (compute capability 10.0+)
                self._check_rtx50_optimizations()

            else:
                self._gpu_available = False
                logger.info("No GPU detected. Running on CPU.")

        except Exception as e:
            self._gpu_available = False
            logger.warning(f"GPU detection failed: {e}. Falling back to CPU.")

    def _check_rtx50_optimizations(self) -> None:
        """Apply optimizations specific to RTX 50 series GPUs."""
        for gpu_name, details in self._gpu_info.items():
            compute_cap = details.get('compute_capability', (0, 0))

            # RTX 50 series (Blackwell) has compute capability 10.0+
            if isinstance(compute_cap, tuple) and compute_cap[0] >= 10:
                logger.info(f"RTX 50 series GPU detected ({gpu_name}). Enabling optimizations.")
                self._enable_rtx50_optimizations()
                break
            # RTX 40 series (Ada Lovelace) has compute capability 8.9
            elif isinstance(compute_cap, tuple) and compute_cap[0] >= 8:
                logger.info(f"RTX 40/30 series GPU detected ({gpu_name}). Enabling optimizations.")
                self._enable_modern_gpu_optimizations()
                break

    def _enable_rtx50_optimizations(self) -> None:
        """Enable RTX 50 series specific optimizations."""
        try:
            # Enable TensorFloat-32 (TF32) for faster matrix operations
            tf.config.experimental.enable_tensor_float_32_execution(True)

            # Enable mixed precision for Blackwell architecture
            # RTX 50 series has excellent FP8/FP16 performance
            self._enable_mixed_precision()

            # Enable XLA JIT compilation for better performance
            tf.config.optimizer.set_jit(True)

            logger.info("RTX 50 series optimizations enabled: TF32, mixed precision, XLA JIT")

        except Exception as e:
            logger.warning(f"Could not enable RTX 50 optimizations: {e}")

    def _enable_modern_gpu_optimizations(self) -> None:
        """Enable optimizations for modern GPUs (RTX 30/40 series)."""
        try:
            # Enable TensorFloat-32 for Ampere+ architectures
            tf.config.experimental.enable_tensor_float_32_execution(True)

            # Enable XLA JIT compilation
            tf.config.optimizer.set_jit(True)

            logger.info("Modern GPU optimizations enabled: TF32, XLA JIT")

        except Exception as e:
            logger.warning(f"Could not enable modern GPU optimizations: {e}")

    def _enable_mixed_precision(self) -> None:
        """Enable mixed precision training/inference."""
        try:
            from tensorflow.keras import mixed_precision

            # Use mixed_float16 for inference (compatible with most GPUs)
            mixed_precision.set_global_policy('mixed_float16')
            self._mixed_precision_enabled = True

            logger.info("Mixed precision (float16) enabled for faster inference")

        except Exception as e:
            logger.warning(f"Could not enable mixed precision: {e}")

    @property
    def is_gpu_available(self) -> bool:
        """Check if GPU is available."""
        return self._gpu_available

    @property
    def gpu_count(self) -> int:
        """Get the number of available GPUs."""
        return len(self._gpu_devices)

    @property
    def gpu_info(self) -> Dict[str, Any]:
        """Get GPU information."""
        return self._gpu_info.copy()

    @property
    def is_mixed_precision_enabled(self) -> bool:
        """Check if mixed precision is enabled."""
        return self._mixed_precision_enabled

    def get_device_strategy(self) -> tf.distribute.Strategy:
        """Get the appropriate distribution strategy for current hardware."""
        if self._gpu_available:
            if len(self._gpu_devices) > 1:
                # Multi-GPU strategy
                return tf.distribute.MirroredStrategy()
            else:
                # Single GPU - use default strategy
                return tf.distribute.get_strategy()
        else:
            # CPU strategy
            return tf.distribute.get_strategy()

    def get_session_config(self) -> Dict[str, Any]:
        """Get TensorFlow session configuration for optimal performance."""
        config = {
            'allow_soft_placement': True,
            'log_device_placement': False,
        }

        if self._gpu_available:
            config['gpu_options'] = {
                'allow_growth': True,
                'per_process_gpu_memory_fraction': 0.9,  # Leave some memory for system
            }

        return config

    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        if self._gpu_available:
            gpu_names = [d.name for d in self._gpu_devices]
            optimizations = []
            if self._memory_growth_enabled:
                optimizations.append("memory growth")
            if self._mixed_precision_enabled:
                optimizations.append("mixed precision")

            opt_str = ", ".join(optimizations) if optimizations else "none"
            return f"GPU Mode: {len(self._gpu_devices)} GPU(s) - {gpu_names}, Optimizations: {opt_str}"
        else:
            return "CPU Mode: No GPU detected, running on CPU"


# Global singleton instance
_gpu_config: Optional[GPUConfig] = None


def initialize_gpu() -> GPUConfig:
    """
    Initialize GPU configuration.

    This should be called once at application startup, before any TensorFlow
    operations. It will detect available GPUs and configure TensorFlow
    appropriately.

    Returns:
        GPUConfig instance with current configuration.
    """
    global _gpu_config
    if _gpu_config is None:
        _gpu_config = GPUConfig()
    return _gpu_config


def get_gpu_config() -> Optional[GPUConfig]:
    """Get the current GPU configuration instance."""
    return _gpu_config


def is_gpu_available() -> bool:
    """Check if GPU is available. Initializes GPU config if not already done."""
    config = initialize_gpu()
    return config.is_gpu_available


def get_device() -> str:
    """Get the appropriate device string for TensorFlow operations."""
    if is_gpu_available():
        return '/GPU:0'
    return '/CPU:0'


def configure_tf_session_for_gpu() -> Dict[str, Any]:
    """
    Get TensorFlow 1.x compatible session configuration.

    This is used for compatibility with the existing TF 1.x style code.

    Returns:
        Dictionary of session configuration options.
    """
    config = initialize_gpu()

    if config.is_gpu_available:
        return {
            'allow_soft_placement': True,
            'log_device_placement': False,
            'gpu_options.allow_growth': True,
            'gpu_options.per_process_gpu_memory_fraction': 0.9,
        }
    else:
        return {
            'allow_soft_placement': True,
            'log_device_placement': False,
        }


def log_gpu_status() -> None:
    """Log the current GPU status."""
    config = initialize_gpu()
    logger.info(config.get_status_summary())
