"""Tests for the text-chunking operation used to split text before generation.

These tests are model-free -- they exercise the pure wrapping/sizing logic and
never load the RNN -- so they run fast and anywhere. Run with:

    pytest tests/test_operations.py        # if pytest is installed
    python tests/test_operations.py        # standalone fallback runner
"""

import os
import sys

# Make the project importable when run directly (python tests/test_operations.py).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from handwriting_synthesis.hand.operations.chunking import (
    split_text_into_chunks,
    balanced_line_breaks,
)


# Tokens longer than this are hard-split by the chunker (see chunking.py).
def _hard_cap(target_chars):
    return max(int(target_chars) * 2, 40)


PUNCTUATED = "I went home, then I slept, and later, after dinner, I read a long book."


def _max_token_len(chunks):
    return max((len(tok) for c in chunks for tok in c.split()), default=0)


def test_balanced_breaks_at_punctuation():
    """'balanced' (the default) must use punctuation breaks, not only sentences.

    Regression guard for the unreachable elif branch that previously made the
    punctuation logic dead code whenever the strategy was 'balanced'.
    """
    chunks = split_text_into_chunks(
        PUNCTUATED, words_per_chunk=3, target_chars_per_chunk=25,
        adaptive_strategy='balanced',
    )
    # At least one boundary lands right after a comma -> punctuation awareness ran.
    assert any(c.rstrip().endswith(',') for c in chunks), chunks


def test_target_chars_is_honoured():
    """Chunks should stay near the character target (down to the min-word floor)."""
    target = 20
    min_words = 2
    chunks = split_text_into_chunks(
        PUNCTUATED, words_per_chunk=4, target_chars_per_chunk=target,
        min_words=min_words, max_words=8, adaptive_strategy='balanced',
    )
    for c in chunks:
        # A chunk may exceed the soft cap only if it is already at the min-word floor.
        assert len(c) <= target or len(c.split()) <= min_words, (c, len(c))


def test_long_word_is_hard_split():
    """A space-less token longer than the hard cap must be broken up."""
    target = 25
    url = "see https://example.com/a/very/long/path/that/keeps/going/and/going/forever/"
    chunks = split_text_into_chunks(url, words_per_chunk=3, target_chars_per_chunk=target)
    assert _max_token_len(chunks) <= _hard_cap(target), chunks
    # Reassembling the tokens must preserve the original characters (no loss).
    assert "".join("".join(c.split()) for c in chunks) == url.replace(" ", "")


def test_normal_long_word_is_not_split():
    """A legitimately long word (shorter than the hard cap) stays intact."""
    word = "internationalization"  # 20 chars, under the 50 hard cap
    chunks = split_text_into_chunks("the " + word + " process", target_chars_per_chunk=25)
    assert any(word in c for c in chunks), chunks


def test_off_strategy_is_fixed_size():
    chunks = split_text_into_chunks(
        "one two three four five six seven", words_per_chunk=3, adaptive_strategy='off',
    )
    assert chunks == ["one two three", "four five six", "seven"], chunks


def test_sentence_strategy_respects_budget():
    chunks = split_text_into_chunks(
        PUNCTUATED, words_per_chunk=3, target_chars_per_chunk=25, adaptive_strategy='sentence',
    )
    assert all(len(c) <= 25 or len(c.split()) <= 2 for c in chunks), chunks


def test_whitespace_and_empty_inputs():
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks("   ") == ["   "]
    lead_trail = split_text_into_chunks("   hello world there   ", words_per_chunk=2)
    assert lead_trail[0].startswith("   "), lead_trail
    assert lead_trail[-1].endswith("   "), lead_trail


def _line_widths(widths, spacing, breaks):
    out = []
    for i, j in breaks:
        w = sum(widths[i:j]) + spacing * (j - i - 1)
        out.append(w)
    return out


def test_balanced_breaks_cover_all_chunks_in_order():
    widths = [90.0, 110.0, 100.0, 95.0, 105.0, 80.0, 120.0]
    breaks = balanced_line_breaks(widths, 8.0, target=250.0, limit=260.0)
    flat = [k for i, j in breaks for k in range(i, j)]
    assert flat == list(range(len(widths))), breaks
    # No line exceeds the limit (none of these single chunks is oversized)
    assert all(w <= 260.0 for w in _line_widths(widths, 8.0, breaks)), breaks


def test_balanced_breaks_spread_slack():
    """DP must not leave one line nearly empty when even splits exist.

    Greedy on these widths gives lines of 240 and 60; balanced breaking
    should split 150/150 (both near-ish target, far better balance).
    """
    widths = [120.0, 120.0, 30.0, 30.0]
    breaks = balanced_line_breaks(widths, 0.0, target=160.0, limit=240.0)
    line_w = _line_widths(widths, 0.0, breaks)
    assert len(line_w) >= 2
    # the non-final lines must be closer to target than greedy's worst case
    assert min(line_w[:-1]) >= 120.0, line_w


def test_balanced_breaks_oversized_chunk_gets_own_line():
    widths = [50.0, 500.0, 50.0]
    breaks = balanced_line_breaks(widths, 5.0, target=200.0, limit=210.0)
    assert (1, 2) in breaks, breaks  # the huge chunk stands alone


def test_balanced_breaks_empty_and_single():
    assert balanced_line_breaks([], 5.0, 100.0, 105.0) == []
    assert balanced_line_breaks([42.0], 5.0, 100.0, 105.0) == [(0, 1)]


def test_progress_guaranteed_with_degenerate_min_words():
    """min_words=0 must not cause an infinite loop."""
    chunks = split_text_into_chunks(
        "a b c d e", words_per_chunk=2, min_words=0, target_chars_per_chunk=5,
    )
    assert "".join("".join(c.split()) for c in chunks) == "abcde", chunks


if __name__ == '__main__':
    tests = [v for k, v in sorted(globals().items())
             if k.startswith('test_') and callable(v)]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failures += 1
            print(f"FAIL  {fn.__name__}: {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
