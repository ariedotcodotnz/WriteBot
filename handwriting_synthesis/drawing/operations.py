from __future__ import print_function

from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter

alphabet = [
    '\x00', ' ', '!', '"', '#', "'", '(', ')', ',', '-', '.',
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', ':', ';',
    '?', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
    'L', 'M', 'N', 'O', 'P', 'R', 'S', 'T', 'U', 'V', 'W', 'Y',
    'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l',
    'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
    'y', 'z'
]
alphabet_ord = list(map(ord, alphabet))
alpha_to_num = defaultdict(int, list(map(reversed, enumerate(alphabet))))
num_to_alpha = dict(enumerate(alphabet_ord))

MAX_STROKE_LEN = 2400  # Increased from 1200 to allow longer sequences
MAX_CHAR_LEN = 120  # Increased from 75 to allow longer lines (less conservative)


def align(coords):
    """
    Corrects for global slant/offset in handwriting strokes.

    Calculates the global slant of the strokes using linear regression and
    rotates the coordinates to align them horizontally.

    Args:
        coords: Numpy array of shape (N, 3) containing stroke coordinates [x, y, eos].

    Returns:
        Aligned coordinates as a numpy array of shape (N, 3).
    """
    coords = np.copy(coords)
    x, y = coords[:, 0].reshape(-1, 1), coords[:, 1].reshape(-1, 1)
    x = np.concatenate([np.ones([x.shape[0], 1]), x], axis=1)
    offset, slope = np.linalg.inv(x.T.dot(x)).dot(x.T).dot(y).squeeze()
    theta = np.arctan(slope)
    rotation_matrix = np.array(
        [[np.cos(theta), -np.sin(theta)],
         [np.sin(theta), np.cos(theta)]]
    )
    coords[:, :2] = np.dot(coords[:, :2], rotation_matrix) - offset
    return coords


def skew(coords, degrees):
    """
    Skews strokes by a given number of degrees.

    Applies a shear transformation to the stroke coordinates.

    Args:
        coords: Numpy array of shape (N, 3) containing stroke coordinates.
        degrees: The angle in degrees to skew the strokes.

    Returns:
        Skewed coordinates as a numpy array of shape (N, 3).
    """
    coords = np.copy(coords)
    theta = degrees * np.pi / 180
    a = np.array([[np.cos(-theta), 0], [np.sin(-theta), 1]])
    coords[:, :2] = np.dot(coords[:, :2], a)
    return coords


def stretch(coords, x_factor, y_factor):
    """
    Stretches strokes along x and y-axis.

    Args:
        coords: Numpy array of shape (N, 3) containing stroke coordinates.
        x_factor: Scaling factor for the x-axis.
        y_factor: Scaling factor for the y-axis.

    Returns:
        Stretched coordinates as a numpy array of shape (N, 3).
    """
    coords = np.copy(coords)
    coords[:, :2] *= np.array([x_factor, y_factor])
    return coords


def add_noise(coords, scale):
    """
    Adds Gaussian noise to strokes.

    Args:
        coords: Numpy array of shape (N, 3) containing stroke coordinates.
        scale: Standard deviation of the Gaussian noise.

    Returns:
        Coordinates with added noise as a numpy array of shape (N, 3).
    """
    coords = np.copy(coords)
    coords[1:, :2] += np.random.normal(loc=0.0, scale=scale, size=coords[1:, :2].shape)
    return coords


def encode_ascii(ascii_string):
    """
    Encodes an ASCII string to an array of integers.

    Maps characters to their integer indices based on the defined `alphabet`.
    Appends 0 at the end.

    Args:
        ascii_string: The string to encode.

    Returns:
        Numpy array of integer indices.
    """
    return np.array(list(map(lambda x: alpha_to_num[x], ascii_string)) + [0])


def denoise(coords):
    """
    Smoothing filter to mitigate artifacts from data collection.

    Applies a Savitzky-Golay filter to smooth the x and y coordinates of each stroke.

    Args:
        coords: Numpy array of shape (N, 3) containing stroke coordinates.

    Returns:
        Smoothed coordinates as a numpy array of shape (N, 3).
    """
    coords_list = np.split(coords, np.where(coords[:, 2] == 1)[0] + 1, axis=0)
    new_coords = []
    for stroke in coords_list:
        if len(stroke) == 0:
            continue
        # If stroke is shorter than window length, skip smoothing but keep it
        if len(stroke) >= 7:
            x_new = savgol_filter(stroke[:, 0], 7, 3, mode='nearest')
            y_new = savgol_filter(stroke[:, 1], 7, 3, mode='nearest')
            xy_coords = np.hstack([x_new.reshape(-1, 1), y_new.reshape(-1, 1)])
        else:
            xy_coords = stroke[:, :2]
        stroke_out = np.concatenate([xy_coords, stroke[:, 2].reshape(-1, 1)], axis=1)
        new_coords.append(stroke_out)

    if not new_coords:
        return np.empty((0, 3), dtype=coords.dtype if hasattr(coords, 'dtype') else float)
    return np.vstack(new_coords)


def interpolate(coords, factor=2):
    """
    Interpolates strokes using cubic spline interpolation.

    Increases the number of points in each stroke by the given factor.

    Args:
        coords: Numpy array of shape (N, 3) containing stroke coordinates.
        factor: The factor by which to increase the number of points (default: 2).

    Returns:
        Interpolated coordinates as a numpy array.
    """
    coords_list = np.split(coords, np.where(coords[:, 2] == 1)[0] + 1, axis=0)
    new_coords = []
    for stroke in coords_list:
        if len(stroke) == 0:
            continue

        xy_coords = stroke[:, :2]

        if len(stroke) > 3:
            f_x = interp1d(np.arange(len(stroke)), stroke[:, 0], kind='cubic')
            f_y = interp1d(np.arange(len(stroke)), stroke[:, 1], kind='cubic')

            xx = np.linspace(0, len(stroke) - 1, factor * (len(stroke)))
            yy = np.linspace(0, len(stroke) - 1, factor * (len(stroke)))

            x_new = f_x(xx)
            y_new = f_y(yy)

            xy_coords = np.hstack([x_new.reshape(-1, 1), y_new.reshape(-1, 1)])

        stroke_eos = np.zeros([len(xy_coords), 1])
        stroke_eos[-1] = 1.0
        stroke_out = np.concatenate([xy_coords, stroke_eos], axis=1)
        new_coords.append(stroke_out)

    if not new_coords:
        return np.empty((0, 3), dtype=coords.dtype if hasattr(coords, 'dtype') else float)
    return np.vstack(new_coords)


def normalize(offsets):
    """
    Normalizes strokes to median unit norm.

    Args:
        offsets: Numpy array of shape (N, 3) containing stroke offsets.

    Returns:
        Normalized offsets as a numpy array.
    """
    offsets = np.copy(offsets)
    offsets[:, :2] /= np.median(np.linalg.norm(offsets[:, :2], axis=1))
    return offsets


def coords_to_offsets(coords):
    """
    Convert from absolute coordinates to relative offsets.

    Args:
        coords: Numpy array of shape (N, 3) containing [x, y, eos].

    Returns:
        Numpy array of shape (N, 3) containing [dx, dy, eos].
        The first point is (0, 0, 1).
    """
    offsets = np.concatenate([coords[1:, :2] - coords[:-1, :2], coords[1:, 2:3]], axis=1)
    offsets = np.concatenate([np.array([[0, 0, 1]]), offsets], axis=0)
    return offsets


def offsets_to_coords(offsets):
    """
    Convert from relative offsets to absolute coordinates.

    Args:
        offsets: Numpy array of shape (N, 3) containing [dx, dy, eos].

    Returns:
        Numpy array of shape (N, 3) containing [x, y, eos].
    """
    return np.concatenate([np.cumsum(offsets[:, :2], axis=0), offsets[:, 2:3]], axis=1)


def draw(
        offsets,
        ascii_seq=None,
        align_strokes=True,
        denoise_strokes=True,
        interpolation_factor=None,
        save_file=None
):
    """
    Draws the strokes using Matplotlib.

    Args:
        offsets: Stroke offsets to draw.
        ascii_seq: Optional ASCII string to display as title.
        align_strokes: Whether to align the strokes horizontally.
        denoise_strokes: Whether to apply denoising.
        interpolation_factor: Factor for cubic spline interpolation.
        save_file: If provided, saves the plot to this file path instead of showing it.

    Returns:
        None
    """
    strokes = offsets_to_coords(offsets)

    if denoise_strokes:
        strokes = denoise(strokes)

    if interpolation_factor is not None:
        strokes = interpolate(strokes, factor=interpolation_factor)

    if align_strokes:
        strokes[:, :2] = align(strokes[:, :2])

    fig, ax = plt.subplots(figsize=(12, 3))

    stroke = []
    for x, y, eos in strokes:
        stroke.append((x, y))
        if eos == 1:
            coords = zip(*stroke)
            ax.plot(coords[0], coords[1], 'k')
            stroke = []
    if stroke:
        coords = zip(*stroke)
        ax.plot(coords[0], coords[1], 'k')
        stroke = []

    ax.set_xlim(-50, 600)
    ax.set_ylim(-40, 40)

    ax.set_aspect('equal')
    plt.tick_params(
        axis='both',
        left='off',
        top='off',
        right='off',
        bottom='off',
        labelleft='off',
        labeltop='off',
        labelright='off',
        labelbottom='off'
    )

    if ascii_seq is not None:
        if not isinstance(ascii_seq, str):
            ascii_seq = ''.join(list(map(chr, ascii_seq)))
        plt.title(ascii_seq)

    if save_file is not None:
        plt.savefig(save_file)
        print('saved to {}'.format(save_file))
    else:
        plt.show()
    plt.close('all')
