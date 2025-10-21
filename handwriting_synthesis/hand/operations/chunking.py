"""Text chunking logic for improved handwriting generation."""

from typing import List


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
    - 'balanced': Combines word length + punctuation awareness
    - 'off': Fixed chunk sizes (no adaptation)

    This method creates more natural chunks by:
    1. Using more words if they're short (better context for the model)
    2. Using fewer words if they're long (avoid exceeding limits)
    3. Respecting sentence and punctuation boundaries when enabled
    4. Ensuring reasonable min/max bounds

    Args:
        text: Input text to split
        words_per_chunk: Target number of words per chunk (used as baseline)
        target_chars_per_chunk: Target character count per chunk (default: 25)
        min_words: Minimum words per chunk
        max_words: Maximum words per chunk
        adaptive_chunking: Enable adaptive chunking
        adaptive_strategy: Strategy to use ('word_length', 'sentence', 'punctuation', 'balanced', 'off')

    Returns:
        List of text chunks
    """
    words = text.split()
    if not words:
        return []

    # Non-adaptive mode: fixed chunk sizes
    if not adaptive_chunking or adaptive_strategy == 'off':
        chunks = []
        for i in range(0, len(words), words_per_chunk):
            chunk = ' '.join(words[i:i + words_per_chunk])
            chunks.append(chunk)
        return chunks

    chunks = []
    i = 0

    # Sentence boundary markers
    sentence_enders = {'.', '!', '?'}
    punctuation_breaks = {',', ';', ':', '--'}

    while i < len(words):
        # Start with the target words per chunk
        chunk_word_count = words_per_chunk

        # Look ahead to see the average word length
        lookahead_end = min(i + words_per_chunk * 2, len(words))
        lookahead_words = words[i:lookahead_end]

        # Word length adaptation (used in word_length and balanced strategies)
        if adaptive_strategy in ('word_length', 'balanced') and lookahead_words:
            avg_word_length = sum(len(w) for w in lookahead_words) / len(lookahead_words)

            # Adjust chunk size based on word length
            if avg_word_length < 4:  # Short words (a, an, the, is, of, etc.)
                # Use more words to provide better context
                chunk_word_count = min(max_words, int(words_per_chunk * 1.5))
            elif avg_word_length > 7:  # Long words
                # Use fewer words to avoid too long chunks
                chunk_word_count = max(min_words, int(words_per_chunk * 0.75))

        # Ensure we stay within bounds
        chunk_word_count = max(min_words, min(max_words, chunk_word_count))

        # Don't exceed remaining words
        chunk_word_count = min(chunk_word_count, len(words) - i)

        # Sentence-aware chunking (sentence and balanced strategies)
        if adaptive_strategy in ('sentence', 'balanced'):
            # Look for sentence boundaries within our chunk range
            search_end = min(i + max_words, len(words))
            for j in range(i + min_words, search_end):
                word = words[j]
                # Check if word ends with sentence terminator
                if any(word.endswith(char) for char in sentence_enders):
                    # Found sentence end, use this as chunk boundary
                    chunk_word_count = j - i + 1
                    break

        # Punctuation-aware chunking (punctuation and balanced strategies)
        elif adaptive_strategy in ('punctuation', 'balanced'):
            # Look for punctuation breaks within our chunk range
            search_start = i + min_words
            search_end = min(i + chunk_word_count + 2, len(words))
            best_break = None

            for j in range(search_start, search_end):
                word = words[j]
                # Check for sentence enders first (higher priority)
                if any(word.endswith(char) for char in sentence_enders):
                    best_break = j - i + 1
                    break
                # Check for punctuation breaks (lower priority)
                elif any(word.endswith(char) for char in punctuation_breaks):
                    best_break = j - i + 1

            if best_break:
                chunk_word_count = best_break

        # Final bounds check
        chunk_word_count = max(min_words, min(max_words, chunk_word_count))
        chunk_word_count = min(chunk_word_count, len(words) - i)

        # Create the chunk
        chunk_words = words[i:i + chunk_word_count]
        chunk_text = ' '.join(chunk_words)

        # If chunk is too long (> 50 chars), split it
        if len(chunk_text) > 50 and len(chunk_words) > min_words:
            # Use fewer words
            chunk_word_count = max(min_words, len(chunk_words) // 2)
            chunk_words = words[i:i + chunk_word_count]
            chunk_text = ' '.join(chunk_words)

        chunks.append(chunk_text)
        i += chunk_word_count

    return chunks
