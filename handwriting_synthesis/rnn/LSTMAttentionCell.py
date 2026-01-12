from collections import namedtuple
import warnings

import numpy as np
import tensorflow as tf
import tensorflow.compat.v1 as tfcompat
import tensorflow_probability as tfp

from handwriting_synthesis.tf.utils import dense_layer, shape

# Suppress TensorFlow deprecation warnings for intentional TF1 compatibility mode usage
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='tensorflow')

tfcompat.disable_v2_behavior()

# Handle Keras 3 compatibility - RNNCell and LSTMCell moved to different location
try:
    # Try the TF1 compat path first
    _RNNCellBase = tfcompat.nn.rnn_cell.RNNCell
    _LSTMCell = tfcompat.nn.rnn_cell.LSTMCell
except AttributeError:
    try:
        # Fallback for Keras 3 / newer TensorFlow
        from tensorflow.python.ops.rnn_cell_impl import RNNCell as _RNNCellBase
        from tensorflow.python.ops.rnn_cell_impl import LSTMCell as _LSTMCell
    except ImportError:
        try:
            # Try tf_keras legacy cells
            from tf_keras.src.layers.rnn.legacy_cells import RNNCell as _RNNCellBase
            from tf_keras.src.layers.rnn.legacy_cells import LSTMCell as _LSTMCell
        except ImportError:
            # Last resort - use minimal base class and basic LSTM
            class _RNNCellBase:
                """Minimal RNNCell base for Keras 3 compatibility."""
                @property
                def state_size(self):
                    raise NotImplementedError

                @property
                def output_size(self):
                    raise NotImplementedError

                def __call__(self, inputs, state, scope=None):
                    raise NotImplementedError

            # Use tf.keras LSTM as fallback
            _LSTMCell = tf.keras.layers.LSTMCell


LSTMAttentionCellState = namedtuple(
    'LSTMAttentionCellState',
    ['h1', 'c1', 'h2', 'c2', 'h3', 'c3', 'alpha', 'beta', 'kappa', 'w', 'phi']
)


class LSTMAttentionCell(_RNNCellBase):
    """
    Custom LSTM cell with attention mechanism for handwriting synthesis.

    This cell implements a multi-layer LSTM (3 layers) with a Gaussian-based
    attention mechanism that attends to the input character sequence.
    """

    def __init__(
            self,
            lstm_size,
            num_attn_mixture_components,
            attention_values,
            attention_values_lengths,
            num_output_mixture_components,
            bias,
            reuse=None,
    ):
        """
        Initialize the LSTMAttentionCell.

        Args:
            lstm_size: Number of units in the LSTM layers.
            num_attn_mixture_components: Number of Gaussian components for attention window.
            attention_values: The character sequence to attend to (one-hot encoded).
            attention_values_lengths: Lengths of the character sequences.
            num_output_mixture_components: Number of mixture components for the output distribution.
            bias: Bias value for controlling handwriting style/clarity.
            reuse: Whether to reuse variables (optional).
        """
        self.reuse = reuse
        self.lstm_size = lstm_size
        self.num_attn_mixture_components = num_attn_mixture_components
        self.attention_values = attention_values
        self.attention_values_lengths = attention_values_lengths
        self.window_size = shape(self.attention_values, 2)
        self.char_len = tf.shape(attention_values)[1]
        self.batch_size = tf.shape(attention_values)[0]
        self.num_output_mixture_components = num_output_mixture_components
        self.output_units = 6 * self.num_output_mixture_components + 1
        self.bias = bias

        # Create LSTM cells once during initialization to avoid deprecation warnings
        self.cell1 = _LSTMCell(self.lstm_size)
        self.cell2 = _LSTMCell(self.lstm_size)
        self.cell3 = _LSTMCell(self.lstm_size)

    @property
    def state_size(self):
        """Returns the size of the state tuple."""
        return LSTMAttentionCellState(
            self.lstm_size,
            self.lstm_size,
            self.lstm_size,
            self.lstm_size,
            self.lstm_size,
            self.lstm_size,
            self.num_attn_mixture_components,
            self.num_attn_mixture_components,
            self.num_attn_mixture_components,
            self.window_size,
            self.char_len,
        )

    @property
    def output_size(self):
        """Returns the size of the output."""
        return self.lstm_size

    def zero_state(self, batch_size, dtype):
        """
        Returns the initial zero state for the cell.

        Args:
            batch_size: The batch size.
            dtype: The data type.

        Returns:
            LSTMAttentionCellState tuple initialized with zeros.
        """
        return LSTMAttentionCellState(
            tf.zeros([batch_size, self.lstm_size]),
            tf.zeros([batch_size, self.lstm_size]),
            tf.zeros([batch_size, self.lstm_size]),
            tf.zeros([batch_size, self.lstm_size]),
            tf.zeros([batch_size, self.lstm_size]),
            tf.zeros([batch_size, self.lstm_size]),
            tf.zeros([batch_size, self.num_attn_mixture_components]),
            tf.zeros([batch_size, self.num_attn_mixture_components]),
            tf.zeros([batch_size, self.num_attn_mixture_components]),
            tf.zeros([batch_size, self.window_size]),
            tf.zeros([batch_size, self.char_len]),
        )

    def __call__(self, inputs, state, scope=None):
        """
        Run the cell one step.

        Args:
            inputs: Input tensor for the current time step.
            state: The previous state of the cell (LSTMAttentionCellState).
            scope: Variable scope.

        Returns:
            Tuple (output, new_state).
        """
        with tfcompat.variable_scope(scope or type(self).__name__, reuse=tfcompat.AUTO_REUSE):
            # lstm 1
            s1_in = tf.concat([state.w, inputs], axis=1)
            s1_out, s1_state = self.cell1(s1_in, state=(state.c1, state.h1))

            # attention
            attention_inputs = tf.concat([state.w, inputs, s1_out], axis=1)
            attention_params = dense_layer(attention_inputs, 3 * self.num_attn_mixture_components, scope='attention')
            alpha, beta, kappa = tf.split(tf.nn.softplus(attention_params), 3, axis=1)
            kappa = state.kappa + kappa / 25.0
            beta = tf.clip_by_value(beta, .01, np.inf)

            kappa_flat, alpha_flat, beta_flat = kappa, alpha, beta
            kappa, alpha, beta = tf.expand_dims(kappa, 2), tf.expand_dims(alpha, 2), tf.expand_dims(beta, 2)

            enum = tf.reshape(tf.range(self.char_len), (1, 1, self.char_len))
            u = tf.cast(tf.tile(enum, (self.batch_size, self.num_attn_mixture_components, 1)), tf.float32)
            phi_flat = tf.reduce_sum(alpha * tf.exp(-tf.square(kappa - u) / beta), axis=1)

            phi = tf.expand_dims(phi_flat, 2)
            sequence_mask = tf.cast(tf.sequence_mask(self.attention_values_lengths, maxlen=self.char_len), tf.float32)
            sequence_mask = tf.expand_dims(sequence_mask, 2)
            w = tf.reduce_sum(phi * self.attention_values * sequence_mask, axis=1)

            # lstm 2
            s2_in = tf.concat([inputs, s1_out, w], axis=1)
            s2_out, s2_state = self.cell2(s2_in, state=(state.c2, state.h2))

            # lstm 3
            s3_in = tf.concat([inputs, s2_out, w], axis=1)
            s3_out, s3_state = self.cell3(s3_in, state=(state.c3, state.h3))

            new_state = LSTMAttentionCellState(
                s1_state.h,
                s1_state.c,
                s2_state.h,
                s2_state.c,
                s3_state.h,
                s3_state.c,
                alpha_flat,
                beta_flat,
                kappa_flat,
                w,
                phi_flat,
            )

            return s3_out, new_state

    def output_function(self, state):
        """
        Computes the output of the cell (stroke parameters) from the state.

        Args:
            state: The current state of the cell.

        Returns:
            Sampled stroke parameters (coords and pen lift).
        """
        params = dense_layer(state.h3, self.output_units, scope='gmm', reuse=tfcompat.AUTO_REUSE)
        pis, mus, sigmas, rhos, es = self._parse_parameters(params)
        mu1, mu2 = tf.split(mus, 2, axis=1)
        mus = tf.stack([mu1, mu2], axis=2)
        sigma1, sigma2 = tf.split(sigmas, 2, axis=1)

        covar_matrix = [tf.square(sigma1), rhos * sigma1 * sigma2,
                        rhos * sigma1 * sigma2, tf.square(sigma2)]
        covar_matrix = tf.stack(covar_matrix, axis=2)
        covar_matrix = tf.reshape(covar_matrix, (self.batch_size, self.num_output_mixture_components, 2, 2))

        mvn = tfp.distributions.MultivariateNormalFullCovariance(loc=mus, covariance_matrix=covar_matrix)
        b = tfp.distributions.Bernoulli(probs=es)
        c = tfp.distributions.Categorical(probs=pis)

        sampled_e = b.sample()
        sampled_coords = mvn.sample()
        sampled_idx = c.sample()

        idx = tf.stack([tf.range(self.batch_size), sampled_idx], axis=1)
        coords = tf.gather_nd(sampled_coords, idx)
        return tf.concat([coords, tf.cast(sampled_e, tf.float32)], axis=1)

    def termination_condition(self, state):
        """
        Determines if the generation should stop.

        Args:
            state: The current state of the cell.

        Returns:
            Boolean tensor indicating if generation is finished for each batch item.
        """
        char_idx = tf.cast(tf.argmax(state.phi, axis=1), tf.int32)
        final_char = char_idx >= self.attention_values_lengths - 1
        past_final_char = char_idx >= self.attention_values_lengths
        output = self.output_function(state)
        es = tf.cast(output[:, 2], tf.int32)
        is_eos = tf.equal(es, tf.ones_like(es))
        return tf.logical_or(tf.logical_and(final_char, is_eos), past_final_char)

    def _parse_parameters(self, gmm_params, eps=1e-8, sigma_eps=1e-4):
        """
        Parses raw output parameters into mixture distribution parameters.

        Args:
            gmm_params: Raw output from the dense layer.
            eps: Epsilon for stability.
            sigma_eps: Minimum value for sigma.

        Returns:
            Tuple (pis, mus, sigmas, rhos, es).
        """
        pis, sigmas, rhos, mus, es = tf.split(
            gmm_params,
            [
                1 * self.num_output_mixture_components,
                2 * self.num_output_mixture_components,
                1 * self.num_output_mixture_components,
                2 * self.num_output_mixture_components,
                1
            ],
            axis=-1
        )
        pis = pis * (1 + tf.expand_dims(self.bias, 1))
        sigmas = sigmas - tf.expand_dims(self.bias, 1)

        pis = tf.nn.softmax(pis, axis=-1)
        pis = tfcompat.where(pis < .01, tf.zeros_like(pis), pis)
        sigmas = tf.clip_by_value(tf.exp(sigmas), sigma_eps, np.inf)
        rhos = tf.clip_by_value(tf.tanh(rhos), eps - 1.0, 1.0 - eps)
        es = tf.clip_by_value(tf.nn.sigmoid(es), eps, 1.0 - eps)
        es = tfcompat.where(es < .01, tf.zeros_like(es), es)

        return pis, mus, sigmas, rhos, es
