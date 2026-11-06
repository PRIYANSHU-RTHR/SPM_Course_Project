"""Prompt templates live here as `<name>.txt` and are loaded by name.

Templates use `string.Template` placeholders (`$brief`, `${skills}`) so literal JSON braces in a
prompt never need escaping. A missing placeholder value raises instead of silently rendering.
"""

import re
from pathlib import Path
from string import Template

PROMPTS_DIR = Path(__file__).resolve().parent
_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class PromptNotFoundError(LookupError):
    pass


def load_prompt(name: str, /, prompts_dir: Path = PROMPTS_DIR, **values: object) -> str:
    """Read `<prompts_dir>/<name>.txt` and substitute `values` into it."""
    if not _NAME.match(name):
        raise ValueError(f"invalid prompt name {name!r}: use lowercase letters, digits and _")
    path = prompts_dir / f"{name}.txt"
    if not path.is_file():
        raise PromptNotFoundError(f"prompt {name!r} not found at {path}")
    return Template(path.read_text(encoding="utf-8")).substitute(
        {key: str(value) for key, value in values.items()}
    )
