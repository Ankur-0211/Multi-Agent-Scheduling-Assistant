"""
Shared helper for reading LLM response content safely.
Gemini 3+ models can return response.content as either a plain string
or a list of content blocks (e.g. [{'type': 'text', 'text': '...', 'extras': {...}}]
when thinking/signatures are involved). This flattens either case to a
plain string so downstream code never has to special-case it.
"""


def extract_text_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)