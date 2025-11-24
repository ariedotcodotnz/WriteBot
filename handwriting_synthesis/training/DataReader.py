"""Data reader for loading and splitting handwriting datasets."""

from __future__ import print_function

import os
import warnings

import numpy as np
import tensorflow.compat.v1 as tfcompat

from handwriting_synthesis.data_frame import DataFrame
from handwriting_synthesis.training.batch_generator import batch_generator

# Suppress TensorFlow deprecation warnings for intentional TF1 compatibility mode usage
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='tensorflow')

tfcompat.disable_v2_behavior()


class DataReader(object):
    """
    Handles loading, splitting, and serving of handwriting data.

    Loads data from numpy files, splits it into train/val/test sets,
    and provides generators for batching.
    """

    def __init__(self, data_dir):
        """
        Initialize the DataReader.

        Args:
            data_dir: Directory containing the preprocessed .npy data files
                      ('x.npy', 'x_len.npy', 'c.npy', 'c_len.npy').
        """
        data_cols = ['x', 'x_len', 'c', 'c_len']
        data = [np.load(os.path.join(data_dir, '{}.npy'.format(i))) for i in data_cols]

        self.test_df = DataFrame(columns=data_cols, data=data)
        self.train_df, self.val_df = self.test_df.train_test_split(train_size=0.95, random_state=2018)

        print('train size', len(self.train_df))
        print('val size', len(self.val_df))
        print('test size', len(self.test_df))

    def train_batch_generator(self, batch_size):
        """
        Get a generator for training batches.

        Args:
            batch_size: Batch size.

        Returns:
            Generator yielding batches.
        """
        return batch_generator(
            batch_size=batch_size,
            df=self.train_df,
            shuffle=True,
            num_epochs=10000,
            mode='train'
        )

    def val_batch_generator(self, batch_size):
        """
        Get a generator for validation batches.

        Args:
            batch_size: Batch size.

        Returns:
            Generator yielding batches.
        """
        return batch_generator(
            batch_size=batch_size,
            df=self.val_df,
            shuffle=True,
            num_epochs=10000,
            mode='val'
        )

    def test_batch_generator(self, batch_size):
        """
        Get a generator for test batches.

        Args:
            batch_size: Batch size.

        Returns:
            Generator yielding batches.
        """
        return batch_generator(
            batch_size=batch_size,
            df=self.test_df,
            shuffle=False,
            num_epochs=1,
            mode='test'
        )
