"""RNN sampling operations for handwriting generation."""

from typing import List, Optional
import numpy as np

from handwriting_synthesis import drawing
from handwriting_synthesis.config import style_path


def sample_strokes(
    rnn_session,
    rnn_model,
    lines: List[str],
    biases: Optional[List[float]] = None,
    styles: Optional[List[int]] = None,
    return_char_indices: bool = False
) -> List[np.ndarray]:
    """
    Sample stroke sequences from the RNN model.

    This function feeds the text input and style configuration into the RNN
    and retrieves the generated stroke sequences.

    Args:
        rnn_session: TensorFlow session.
        rnn_model: RNN model with necessary placeholders.
        lines: List of text lines to generate.
        biases: Optional list of bias values (one per line). Bias controls the
                consistency of the handwriting. Higher bias -> more legible,
                less random.
        styles: Optional list of style IDs (one per line).
        return_char_indices: If True, also return the character indices per stroke
                             (from the attention mechanism's phi weights).

    Returns:
        If return_char_indices is False:
            List of stroke sequences (numpy arrays of shape [T, 3]).
            Each stroke point is (x, y, eos).
        If return_char_indices is True:
            Tuple of (strokes_list, char_indices_list) where char_indices_list
            contains the character index the model was attending to at each stroke.
    """
    num_samples = len(lines)
    max_tsteps = 40 * max([len(i) for i in lines])
    biases = biases if biases is not None else [0.5] * num_samples

    x_prime = np.zeros([num_samples, drawing.MAX_STROKE_LEN, 3])
    x_prime_len = np.zeros([num_samples])
    chars = np.zeros([num_samples, 120])
    chars_len = np.zeros([num_samples])

    if styles is not None:
        for i, (cs, style) in enumerate(zip(lines, styles)):
            x_p = np.load(f"{style_path}/style-{style}-strokes.npy")
            c_p = np.load(f"{style_path}/style-{style}-chars.npy").tostring().decode('utf-8')

            c_p = str(c_p) + " " + cs
            c_p = drawing.encode_ascii(c_p)
            c_p = np.array(c_p)

            x_prime[i, :len(x_p), :] = x_p
            x_prime_len[i] = len(x_p)
            chars[i, :len(c_p)] = c_p
            chars_len[i] = len(c_p)

    else:
        for i in range(num_samples):
            encoded = drawing.encode_ascii(lines[i])
            chars[i, :len(encoded)] = encoded
            chars_len[i] = len(encoded)

    feed_dict = {
        rnn_model.prime: styles is not None,
        rnn_model.x_prime: x_prime,
        rnn_model.x_prime_len: x_prime_len,
        rnn_model.num_samples: num_samples,
        rnn_model.sample_tsteps: max_tsteps,
        rnn_model.c: chars,
        rnn_model.c_len: chars_len,
        rnn_model.bias: biases
    }

    if return_char_indices:
        # Fetch both stroke samples and character indices from attention
        samples, char_indices = rnn_session.run(
            [rnn_model.sampled_sequence, rnn_model.sampled_char_indices],
            feed_dict=feed_dict
        )
        # Remove zero-padded strokes (and corresponding char indices)
        strokes_list = []
        char_indices_list = []
        for sample, ci in zip(samples, char_indices):
            # Find non-zero strokes
            valid_mask = ~np.all(sample == 0.0, axis=1)
            strokes_list.append(sample[valid_mask])
            char_indices_list.append(ci[valid_mask])
        return strokes_list, char_indices_list
    else:
        # Original behavior: only fetch stroke samples
        [samples] = rnn_session.run(
            [rnn_model.sampled_sequence],
            feed_dict=feed_dict
        )
        samples = [sample[~np.all(sample == 0.0, axis=1)] for sample in samples]
        return samples
