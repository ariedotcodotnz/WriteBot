"""Text chunking logic for improved handwriting generation."""

from typing import List, Optional


# Tokens that mark the end of a sentence -- strong, high-priority break points.
_SENTENCE_ENDERS = ('.', '!', '?')
# Softer break points; a comma/semicolon is a natural place to end a chunk.
_PUNCTUATION_BREAKS = (',', ';', ':')


def _hard_split_long_word(word: str, max_chars: int) -> List[str]:
    """Break a single token longer than ``max_chars`` into ``<= max_chars`` pieces.

    Normal words are returned unchanged. This only triggers for pathological
    tokens (URLs, long identifiers, base64 blobs) that would otherwise create an
    over-long RNN sequence or run off the edge of the page, since such a token
    contains no spaces for the wrapper to break on.

    Args:
        word: The token to (possibly) split.
        max_chars: Maximum characters allowed per piece.

    Returns:
        List of one or more sub-tokens, each at most ``max_chars`` long.
    """
    if max_chars <= 0 or len(word) <= max_chars:
        return [word]
    return [word[i:i + max_chars] for i in range(0, len(word), max_chars)]


def _find_break_point(
    words: List[str],
    start: int,
    search_lo: int,
    search_hi: int,
    use_sentence: bool,
    use_punctuation: bool,
) -> Optional[int]:
    """Find a punctuation-based chunk boundary within a word range.

    Sentence terminators take priority and break as early as possible (so a
    sentence becomes its own chunk). Failing that, the *latest* soft punctuation
    break in range is used, which fills the chunk as much as possible while still
    ending on a natural pause.

    Args:
        words: Full list of words.
        start: Index of the first word in the current chunk.
        search_lo: First word index to consider as a break point.
        search_hi: One past the last word index to consider.
        use_sentence: Whether to break on sentence terminators (. ! ?).
        use_punctuation: Whether to break on soft punctuation (, ; :).

    Returns:
        A word count for the chunk if a break was found, otherwise ``None``.
    """
    punctuation_break = None
    for j in range(search_lo, search_hi):
        word = words[j]
        if use_sentence and word.endswith(_SENTENCE_ENDERS):
            return j - start + 1
        if use_punctuation and word.endswith(_PUNCTUATION_BREAKS):
            punctuation_break = j - start + 1  # keep the latest one in range
    return punctuation_break


def split_text_into_chunks(
    text: str,
    words_per_chunk: int = 4,
    target_chars_per_chunk: int = 25,
    min_words: int = 2,
    max_words: int = 8,
    adaptive_chunking: bool = True,
    adaptive_strategy: str = 'balanced'
) -> List[str]:
    """
    Split text into chunks with adaptive sizing based on selected strategy.

    Adaptive strategies:
    - 'word_length': Adjusts based on average word length (original behavior)
    - 'sentence': Respects sentence boundaries (periods, !, ?)
    - 'punctuation': Prefers to break at punctuation marks (commas, semicolons)
    - 'balanced': Combines word length + sentence + punctuation awareness
    - 'off': Fixed chunk sizes (no adaptation)

    This method creates more natural chunks by:
    1. Using more words if they're short (better context for the model)
    2. Using fewer words if they're long (avoid exceeding limits)
    3. Respecting sentence and punctuation boundaries when enabled
    4. Keeping chunk length near ``target_chars_per_chunk`` for even line filling
    5. Ensuring reasonable min/max bounds

    Args:
        text: Input text to split.
        words_per_chunk: Target number of words per chunk (used as baseline).
        target_chars_per_chunk: Soft upper bound on characters per chunk. Chunks
            are trimmed back toward this length (never below ``min_words``) so the
            generated pieces stay a consistent size.
        min_words: Minimum words per chunk.
        max_words: Maximum words per chunk.
        adaptive_chunking: Enable adaptive chunking.
        adaptive_strategy: Strategy to use ('word_length', 'sentence', 'punctuation', 'balanced', 'off').

    Returns:
        List of text chunks.
    """
    # Preserve leading/trailing whitespace
    leading_space = len(text) - len(text.lstrip())
    trailing_space = len(text) - len(text.rstrip())

    raw_words = text.split()
    if not raw_words:
        # If only whitespace, return it as-is
        return [text] if text else []

    # Character budgets. The soft cap keeps chunks near the requested target; the
    # hard cap only breaks pathological space-less tokens so they cannot blow past
    # the model's sequence limit. A normal long word (e.g. "internationalization")
    # stays intact because it is shorter than the hard cap.
    soft_char_cap = max(1, int(target_chars_per_chunk))
    hard_word_cap = max(soft_char_cap * 2, 40)

    # Pre-split any token that is, on its own, longer than the hard cap. For normal
    # text this is a no-op, so word-based logic below is unchanged.
    words: List[str] = []
    for w in raw_words:
        words.extend(_hard_split_long_word(w, hard_word_cap))

    def _chunk_char_len(start: int, count: int) -> int:
        """Character length of ``count`` words joined with single spaces."""
        return len(' '.join(words[start:start + count]))

    def _fit_to_char_budget(start: int, count: int) -> int:
        """Shrink ``count`` so the chunk fits the soft char cap (keeps >= min_words)."""
        lower_bound = min(min_words, len(words) - start)
        while count > lower_bound and _chunk_char_len(start, count) > soft_char_cap:
            count -= 1
        return max(1, count)

    # Non-adaptive mode: fixed chunk sizes (still honours the hard word cap above).
    if not adaptive_chunking or adaptive_strategy == 'off':
        chunks = []
        for i in range(0, len(words), words_per_chunk):
            chunk = ' '.join(words[i:i + words_per_chunk])
            # Add leading space to first chunk
            if i == 0 and leading_space > 0:
                chunk = ' ' * leading_space + chunk
            # Add trailing space to last chunk
            if i + words_per_chunk >= len(words) and trailing_space > 0:
                chunk = chunk + ' ' * trailing_space
            chunks.append(chunk)
        return chunks

    chunks = []
    i = 0

    use_sentence = adaptive_strategy in ('sentence', 'balanced')
    use_punctuation = adaptive_strategy in ('punctuation', 'balanced')
    use_word_length = adaptive_strategy in ('word_length', 'balanced')
    # A sentence terminator is a strong break for ANY punctuation-aware strategy
    # (sentence / punctuation / balanced); soft commas/semicolons only break when
    # punctuation awareness is on. NOTE: 'balanced' must consider both -- the old
    # if/elif on overlapping sets made the punctuation branch unreachable for it
    # (and 'balanced' is the default strategy).
    break_on_sentence = use_sentence or use_punctuation

    while i < len(words):
        remaining = len(words) - i

        # 1. Baseline chunk size, optionally adapted to average word length so that
        #    short words pack more per chunk and long words pack fewer.
        chunk_word_count = words_per_chunk
        if use_word_length:
            lookahead_words = words[i:min(i + words_per_chunk * 2, len(words))]
            if lookahead_words:
                avg_word_length = sum(len(w) for w in lookahead_words) / len(lookahead_words)
                if avg_word_length < 4:                       # short words
                    chunk_word_count = min(max_words, int(words_per_chunk * 1.5))
                elif avg_word_length > 7:                     # long words
                    chunk_word_count = max(min_words, int(words_per_chunk * 0.75))
        chunk_word_count = max(min_words, min(max_words, chunk_word_count))
        chunk_word_count = min(chunk_word_count, remaining)

        # 2. Character budget: the most words that still fit the soft cap. This
        #    bounds everything below so chunks stay near target_chars_per_chunk.
        budget_max = _fit_to_char_budget(i, min(max_words, remaining))

        # 3. Prefer a natural break (sentence/punctuation) *within* the budget
        #    window, so the break lands on real punctuation that also fits the
        #    target -- rather than trimming a good break back to mid-phrase.
        if break_on_sentence:
            search_lo = i + min_words
            search_hi = i + min(budget_max, remaining)
            break_point = _find_break_point(
                words, i, search_lo, search_hi, break_on_sentence, use_punctuation
            )
            if break_point:
                chunk_word_count = break_point
            else:
                # No natural break in range: keep the baseline size, capped by budget.
                chunk_word_count = min(chunk_word_count, budget_max)
        else:
            # word_length / off: no punctuation awareness, just honour the budget.
            chunk_word_count = min(chunk_word_count, budget_max)

        # Final bounds: never below the word floor, never past the remaining words,
        # and always at least one word so the loop is guaranteed to make progress.
        chunk_word_count = min(max(min_words, chunk_word_count), remaining)
        chunk_word_count = max(1, chunk_word_count)

        # Create the chunk
        chunk_words = words[i:i + chunk_word_count]
        chunk_text = ' '.join(chunk_words)

        # Add leading space to first chunk
        if i == 0 and leading_space > 0:
            chunk_text = ' ' * leading_space + chunk_text

        # Add trailing space to last chunk
        if i + chunk_word_count >= len(words) and trailing_space > 0:
            chunk_text = chunk_text + ' ' * trailing_space

        chunks.append(chunk_text)
        i += chunk_word_count

    return chunks
