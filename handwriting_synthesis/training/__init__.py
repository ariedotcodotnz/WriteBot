"""
Training module for handwriting synthesis.

This package contains functions and classes for training the RNN model,
including data reading and batch generation.
"""

from .DataReader import DataReader
from .batch_generator import batch_generator
from .train import train
