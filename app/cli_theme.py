"""Memphis-inspired CLI theme for the Atlantis CLI.

256-color safe palette inspired by the Memphis Group design movement (1980s):
bold geometric shapes, high-contrast primaries, playful energy.
"""

from __future__ import annotations

from rich.console import Console
from rich.theme import Theme

# -- Memphis palette (256-color safe) ----------------------------------------

MEMPHIS_THEME = Theme({
    # Core UI elements
    "memphis.title": "bold bright_magenta",
    "memphis.subtitle": "bold bright_cyan",
    "memphis.label": "bold bright_white",
    "memphis.value": "bright_white",
    "memphis.dim": "dim",
    "memphis.hint": "dim italic",
    # Status colors
    "memphis.success": "bold bright_green",
    "memphis.error": "bold bright_red",
    "memphis.warning": "bold bright_yellow",
    "memphis.running": "bold bright_yellow",
    "memphis.info": "bold bright_cyan",
    # Panel borders
    "memphis.border": "bright_magenta",
    "memphis.border.success": "bright_green",
    "memphis.border.error": "bright_red",
    "memphis.border.info": "bright_cyan",
    # Progress / spinners
    "memphis.spinner": "bold bright_magenta",
    "memphis.progress": "bright_cyan",
})

# JSON display uses Pygments 'native' theme: green keys, orange strings,
# blue numbers — high contrast on dark backgrounds, 256-color safe.
JSON_SYNTAX_THEME = "native"

# -- Banner ------------------------------------------------------------------

# Each tuple: (color, line) — color-cycling Memphis banner shaped as a
# stylized E. coli rod cell: elongated capsule body with ⧬ (U+29EC,
# DNA double helix) in the membrane border, flagella bundle trailing
# from the right pole, half-block 90s/BBS font, Memphis dot accent.
# Helix border: alternating teal(⋊⋉) / pink(⋊⋉) with yellow connectors
_T = "[bold dark_cyan]"  # teal (256-color safe)
_P = "[bold hot_pink]"  # 90s pink (256-color safe)
_Y = "[bold gold1]"  # yellow (256-color safe)
_R = "[/]"
_HELIX_TOP = (
    f"     {_Y}╭─{_R}"
    f"{_T}⋊⋉{_R}{_Y}──{_R}{_P}⋊⋉{_R}{_Y}──{_R}{_T}⋊⋉{_R}{_Y}──{_R}"
    f"{_P}⋊⋉{_R}{_Y}──{_R}{_T}⋊⋉{_R}{_Y}──{_R}{_P}⋊⋉{_R}{_Y}──{_R}"
    f"{_T}⋊⋉{_R}{_Y}──{_R}{_P}⋊⋉{_R}{_Y}──{_R}{_T}⋊⋉{_R}{_Y}─╮{_R}"
)
_HELIX_BOT = (
    f"     {_Y}╰─{_R}"
    f"{_P}⋊⋉{_R}{_Y}──{_R}{_T}⋊⋉{_R}{_Y}──{_R}{_P}⋊⋉{_R}{_Y}──{_R}"
    f"{_T}⋊⋉{_R}{_Y}──{_R}{_P}⋊⋉{_R}{_Y}──{_R}{_T}⋊⋉{_R}{_Y}──{_R}"
    f"{_P}⋊⋉{_R}{_Y}──{_R}{_T}⋊⋉{_R}{_Y}──{_R}{_P}⋊⋉{_R}{_Y}─╯{_R}"
)

_BANNER = [
    (None, _HELIX_TOP),
    ("bright_magenta", "   ╭─╯                                            ╰─╮"),
    ("green1", "  ╭╯   ▄▀▄ ▀█▀ █   ▄▀▄ █▄ █ ▀█▀ █ ▄▀▀              ╰╮~∿~∿"),
    ("medium_purple1", " (     █▀█  █  █▄▄ █▀█ █ ▀█  █  █ ▄██    ◌ ◌ ◌       )∿~∿~"),
    ("bright_magenta", "  ╰╮                                               ╭╯~∿~~∿"),
    ("bright_white", "   ╰─╮   ∿ whole-cell simulation platform ∿    ╭─╯∿~∿~"),
    (None, _HELIX_BOT),
]


def print_banner(console: Console) -> None:
    """Print the Memphis-styled color-cycling banner."""
    console.print()
    for color, line in _BANNER:
        if color is None:
            console.print(line)
        else:
            console.print(f"[bold {color}]{line}[/]")
    console.print()


# -- Styled console factory --------------------------------------------------


def get_console() -> Console:
    """Create a Console with the Memphis theme applied.

    Forces 256-color mode to avoid truecolor rendering artifacts in
    terminals with incomplete 24-bit support (e.g. macOS Terminal.app).
    """
    return Console(theme=MEMPHIS_THEME, color_system="256")


# -- Display helpers ----------------------------------------------------------


def display_json(content: dict[str, object] | list[object] | str, console: Console | None = None) -> None:
    """Display JSON data using the 256-color-safe native Pygments theme."""
    import json

    from rich.syntax import Syntax

    if console is None:
        console = get_console()

    if isinstance(content, str):
        console.print(content)
    else:
        formatted = json.dumps(content, indent=2, default=str)
        console.print(Syntax(formatted, "json", theme=JSON_SYNTAX_THEME, line_numbers=False))


def status_style(status: str) -> str:
    """Return the Memphis style name for a given status string."""
    if status in ("completed",):
        return "memphis.success"
    if status in ("failed", "cancelled"):
        return "memphis.error"
    if status in ("running", "pending"):
        return "memphis.running"
    return "memphis.info"


def status_border(status: str) -> str:
    """Return the Memphis border style name for a given status string."""
    if status in ("completed",):
        return "memphis.border.success"
    if status in ("failed", "cancelled"):
        return "memphis.border.error"
    return "memphis.border.info"
