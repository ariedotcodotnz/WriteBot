"""Batch generation logic for training the handwriting model."""

import numpy as np


def batch_generator(batch_size, df, shuffle=True, num_epochs=10000, mode='train'):
    """
    Generates batches of data for training or testing.

    Args:
        batch_size: Size of the batch.
        df: The DataFrame containing the data (handwriting_synthesis.data_frame.DataFrame).
        shuffle: Whether to shuffle the data.
        num_epochs: Number of epochs to generate.
        mode: 'train' or 'test'. If 'test', allows smaller final batch.

    Yields:
        Dictionary containing batch data with keys:
        'x': Input stroke sequences.
        'y': Target stroke sequences (offset by 1 timestep).
        'x_len': Length of stroke sequences.
        'c': Character sequences.
        'c_len': Length of character sequences.
    """
    gen = df.batch_generator(
        batch_size=batch_size,
        shuffle=shuffle,
        num_epochs=num_epochs,
        allow_smaller_final_batch=(mode == 'test')
    )
    for batch in gen:
        batch['x_len'] = batch['x_len'] - 1
        max_x_len = np.max(batch['x_len'])
        max_c_len = np.max(batch['c_len'])
        batch['y'] = batch['x'][:, 1:max_x_len + 1, :]
        batch['x'] = batch['x'][:, :max_x_len, :]
        batch['c'] = batch['c'][:, :max_c_len]
        yield batch
