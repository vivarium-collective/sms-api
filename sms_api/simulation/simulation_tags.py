"""Tag registry for simulation filtering.

Provides a lightweight, extensible mapping from tag names to lists of experiment
IDs. Tags are defined in code (not in the database) to keep the system simple
and zero-migration. If dynamic user-defined tags are needed later, this module
can be replaced with a database-backed solution without changing the API surface.
"""

SIMULATION_TAGS: dict[str, list[str]] = {
    "cd1": [
        "sim31-baseline-60bb",
        "sim33-violacien-seeds1000-generations10-9617",
        "sim33-mecillinam-seeds84-generations10-036f",
    ],
}


def resolve_tag(tag: str) -> list[str]:
    """Resolve a tag name to its list of experiment IDs.

    Args:
        tag: The tag name to resolve (e.g. 'cd1').

    Returns:
        A list of experiment IDs associated with the tag.

    Raises:
        ValueError: If the tag is not found in the registry.
    """
    if tag not in SIMULATION_TAGS:
        available = sorted(SIMULATION_TAGS.keys())
        raise ValueError(f"Unknown simulation tag '{tag}'. Available tags: {available}")
    return SIMULATION_TAGS[tag]
