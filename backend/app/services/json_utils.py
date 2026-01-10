import json


def extract_first_json_object(text: str) -> dict:
    """Best-effort extraction of the first JSON object from a string."""
    s = text.strip()
    if not s:
        raise ValueError("Empty text")

    try:
        val = json.loads(s)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found")

    chunk = s[start : end + 1]
    val = json.loads(chunk)
    if not isinstance(val, dict):
        raise ValueError("Extracted JSON is not an object")
    return val
