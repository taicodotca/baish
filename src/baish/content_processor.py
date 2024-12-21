from .token_counter import count_tokens


def chunk_content(content: str, chunk_size: int) -> list[str]:
    """Split content into chunks based on token count."""
    if not content:
        return [""]

    # Count total tokens first
    total_tokens = count_tokens(content)
    if total_tokens <= chunk_size:
        return [content]

    chunks = []
    current_chunk = []
    current_size = 0

    for line in content.splitlines():
        line_tokens = count_tokens(line + "\n")

        # Handle single long lines
        if line_tokens > chunk_size:
            words = line.split()
            current_word_chunk = []
            current_word_size = 0

            for word in words:
                word_tokens = count_tokens(word + " ")
                if current_word_size + word_tokens > chunk_size:
                    if current_word_chunk:
                        chunks.append(" ".join(current_word_chunk))
                    current_word_chunk = [word]
                    current_word_size = word_tokens
                else:
                    current_word_chunk.append(word)
                    current_word_size += word_tokens

            if current_word_chunk:
                chunks.append(" ".join(current_word_chunk))
            continue

        if current_size + line_tokens > chunk_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_size = line_tokens
        else:
            current_chunk.append(line)
            current_size += line_tokens

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks if chunks else [content]
