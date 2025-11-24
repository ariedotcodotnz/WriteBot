import copy

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


class DataFrame(object):
    """
    Minimal pd.DataFrame analog for handling n-dimensional numpy matrices.

    Provides support for shuffling, batching, and train/test splitting.
    """

    def __init__(self, columns, data):
        """
        Initialize the DataFrame.

        Args:
            columns: List of names corresponding to the matrices in data.
            data: List of n-dimensional data matrices ordered in correspondence with columns.
                All matrices must have the same leading dimension. Data can also be fed a list of
                instances of np.memmap, in which case RAM usage can be limited to the size of a
                single batch.
        """
        assert len(columns) == len(data), 'columns length does not match data length'

        lengths = [mat.shape[0] for mat in data]
        assert len(set(lengths)) == 1, 'all matrices in data must have same first dimension'

        self.length = lengths[0]
        self.columns = columns
        self.data = data
        self.dict = dict(zip(self.columns, self.data))
        self.idx = np.arange(self.length)

    def shapes(self):
        """Returns a pandas Series containing the shapes of each column."""
        return pd.Series(dict(zip(self.columns, [mat.shape for mat in self.data])))

    def dtypes(self):
        """Returns a pandas Series containing the dtype of each column."""
        return pd.Series(dict(zip(self.columns, [mat.dtype for mat in self.data])))

    def shuffle(self):
        """Shuffles the indices in-place."""
        np.random.shuffle(self.idx)

    def train_test_split(self, train_size, random_state=np.random.randint(1000), stratify=None):
        """
        Splits the DataFrame into train and test sets.

        Args:
            train_size: Proportion of the dataset to include in the train split.
            random_state: Seed for random number generator.
            stratify: Data to use for stratification.

        Returns:
            Tuple (train_df, test_df).
        """
        train_idx, test_idx = train_test_split(
            self.idx,
            train_size=train_size,
            random_state=random_state,
            stratify=stratify
        )
        train_df = DataFrame(copy.copy(self.columns), [mat[train_idx] for mat in self.data])
        test_df = DataFrame(copy.copy(self.columns), [mat[test_idx] for mat in self.data])
        return train_df, test_df

    def batch_generator(self, batch_size, shuffle=True, num_epochs=10000, allow_smaller_final_batch=False):
        """
        Generates batches of data.

        Args:
            batch_size: Size of each batch.
            shuffle: Whether to shuffle data at the beginning of each epoch.
            num_epochs: Number of epochs to generate batches for.
            allow_smaller_final_batch: Whether to yield the final batch if it's smaller than batch_size.

        Yields:
            DataFrame containing the batch data.
        """
        epoch_num = 0
        while epoch_num < num_epochs:
            if shuffle:
                self.shuffle()

            for i in range(0, self.length + 1, batch_size):
                batch_idx = self.idx[i: i + batch_size]
                if not allow_smaller_final_batch and len(batch_idx) != batch_size:
                    break
                yield DataFrame(
                    columns=copy.copy(self.columns),
                    data=[mat[batch_idx].copy() for mat in self.data]
                )

            epoch_num += 1

    def iterrows(self):
        """Iterates over the rows of the DataFrame."""
        for i in self.idx:
            yield self[i]

    def mask(self, mask):
        """
        Returns a new DataFrame with rows selected by the boolean mask.

        Args:
            mask: Boolean array matching the length of the DataFrame.

        Returns:
            Filtered DataFrame.
        """
        return DataFrame(copy.copy(self.columns), [mat[mask] for mat in self.data])

    def concat(self, other_df):
        """
        Concatenates this DataFrame with another along the first axis.

        Args:
            other_df: DataFrame to concatenate.

        Returns:
            New concatenated DataFrame.
        """
        mats = []
        for column in self.columns:
            mats.append(np.concatenate([self[column], other_df[column]], axis=0))
        return DataFrame(copy.copy(self.columns), mats)

    def items(self):
        """Returns an iterator over (column, data) pairs."""
        return self.dict.items()

    def __iter__(self):
        """Returns an iterator over the dictionary items."""
        return self.dict.items().__iter__()

    def __len__(self):
        """Returns the number of rows in the DataFrame."""
        return self.length

    def __getitem__(self, key):
        """
        Get item by key or index.

        Args:
            key: Column name (str) or row index (int).

        Returns:
            The column data (if key is str) or a Series representing the row (if key is int).
        """
        if isinstance(key, str):
            return self.dict[key]

        elif isinstance(key, int):
            return pd.Series(dict(zip(self.columns, [mat[self.idx[key]] for mat in self.data])))

    def __setitem__(self, key, value):
        """
        Set a column.

        Args:
            key: Column name.
            value: Data array.
        """
        assert value.shape[0] == len(self), 'matrix first dimension does not match'
        if key not in self.columns:
            self.columns.append(key)
            self.data.append(value)
        self.dict[key] = value
