"""Small tag-index helper used by the prerelease smoke fixture."""


def merge_tags(existing, incoming):
    """Return unique tags from both inputs."""

    return sorted(set(existing) | set(incoming))
