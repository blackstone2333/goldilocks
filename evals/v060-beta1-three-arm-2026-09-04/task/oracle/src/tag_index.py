"""Small tag-index helper used by the prerelease smoke fixture."""


def merge_tags(existing, incoming):
    """Return normalized unique tags in first-seen order."""

    merged = []
    seen = set()
    for raw_tag in list(existing) + list(incoming):
        tag = raw_tag.strip()
        key = tag.casefold()
        if not tag or key in seen:
            continue
        seen.add(key)
        merged.append(tag)
    return merged
