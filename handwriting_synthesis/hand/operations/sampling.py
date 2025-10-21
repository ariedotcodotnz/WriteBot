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
    styles: Optional[List[int]] = None
) -> List[np.ndarray]:
    """
    Sample stroke sequences from the RNN model.

    Args:
        rnn_session: TensorFlow session
        rnn_model: RNN model with necessary placeholders
        lines: List of text lines to generate
        biases: Optional list of bias values (one per line)
        styles: Optional list of style IDs (one per line)

    Returns:
        List of stroke sequences (numpy arrays)
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

    [samples] = rnn_session.run(
        [rnn_model.sampled_sequence],
        feed_dict={
            rnn_model.prime: styles is not None,
            rnn_model.x_prime: x_prime,
            rnn_model.x_prime_len: x_prime_len,
            rnn_model.num_samples: num_samples,
            rnn_model.sample_tsteps: max_tsteps,
            rnn_model.c: chars,
            rnn_model.c_len: chars_len,
            rnn_model.bias: biases
        }
    )
    samples = [sample[~np.all(sample == 0.0, axis=1)] for sample in samples]
    return samples
