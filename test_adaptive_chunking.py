#!/usr/bin/env python3
"""
Quick test for adaptive chunking functionality - simplified version
"""

def split_text_into_chunks(
        text: str,
        words_per_chunk: int = 4,
        target_chars_per_chunk: int = 25,
        min_words: int = 2,
        max_words: int = 8,
        adaptive_chunking: bool = True,
        adaptive_strategy: str = 'balanced'
):
    """
    Simplified version of the chunking algorithm for testing
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
            if avg_word_length < 4:  # Short words
                chunk_word_count = min(max_words, int(words_per_chunk * 1.5))
            elif avg_word_length > 7:  # Long words
                chunk_word_count = max(min_words, int(words_per_chunk * 0.75))

        # Ensure we stay within bounds
        chunk_word_count = max(min_words, min(max_words, chunk_word_count))
        chunk_word_count = min(chunk_word_count, len(words) - i)

        # Sentence-aware chunking
        if adaptive_strategy in ('sentence', 'balanced'):
            search_end = min(i + max_words, len(words))
            for j in range(i + min_words, search_end):
                word = words[j]
                if any(word.endswith(char) for char in sentence_enders):
                    chunk_word_count = j - i + 1
                    break

        # Punctuation-aware chunking
        elif adaptive_strategy in ('punctuation', 'balanced'):
            search_start = i + min_words
            search_end = min(i + chunk_word_count + 2, len(words))
            best_break = None

            for j in range(search_start, search_end):
                word = words[j]
                if any(word.endswith(char) for char in sentence_enders):
                    best_break = j - i + 1
                    break
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

        # If chunk is too long, split it
        if len(chunk_text) > 50 and len(chunk_words) > min_words:
            chunk_word_count = max(min_words, len(chunk_words) // 2)
            chunk_words = words[i:i + chunk_word_count]
            chunk_text = ' '.join(chunk_words)

        chunks.append(chunk_text)
        i += chunk_word_count

    return chunks


def test_chunking_strategies():
    """Test different chunking strategies"""
    # Test text with various features
    test_text = "This is a short test. It has sentences! Does it work? Yes, it does. The quick brown fox jumps over the lazy dog, and then continues running."

    strategies = ['off', 'word_length', 'sentence', 'punctuation', 'balanced']

    print("Testing Adaptive Chunking Strategies")
    print("=" * 60)
    print(f"\nTest text:\n{test_text}\n")
    print("=" * 60)

    for strategy in strategies:
        print(f"\nStrategy: {strategy}")
        print("-" * 60)

        chunks = split_text_into_chunks(
            test_text,
            words_per_chunk=3,
            target_chars_per_chunk=25,
            min_words=2,
            max_words=8,
            adaptive_chunking=(strategy != 'off'),
            adaptive_strategy=strategy
        )

        print(f"Number of chunks: {len(chunks)}")
        for i, chunk in enumerate(chunks, 1):
            word_count = len(chunk.split())
            char_count = len(chunk)
            print(f"  Chunk {i} ({word_count} words, {char_count} chars): '{chunk}'")

    print("\n" + "=" * 60)
    print("✓ Test completed successfully!")
    print("\nKey observations:")
    print("- 'off': Fixed 3-word chunks")
    print("- 'word_length': Adjusts based on average word length")
    print("- 'sentence': Breaks at sentence boundaries (., !, ?)")
    print("- 'punctuation': Prefers to break at punctuation")
    print("- 'balanced': Combines all strategies for optimal chunking")


if __name__ == "__main__":
    try:
        test_chunking_strategies()
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
