"""Resolve preserved repository paths after the research-directory migration."""
from pathlib import Path as NativePath
from functools import lru_cache
import json
import os
import sys


@lru_cache(maxsize=1)
def repository_root():
    return next(p for p in NativePath(__file__).resolve().parents if (p / "AGENTS.md").is_file())


@lru_cache(maxsize=1)
def path_map():
    mapping = json.loads((repository_root() / "04_结果/项目记录/目录迁移/path_map.json").read_text(encoding="utf-8"))
    return dict(sorted(mapping.items(), key=lambda item: len(item[0]), reverse=True))


def resolve_legacy(value):
    p = NativePath(os.path.normpath(value))
    root = repository_root()
    if p.is_absolute():
        try:
            rel = p.relative_to(root).as_posix()
        except ValueError:
            return p
    else:
        rel = p.as_posix()
    mapping = path_map()
    parts = rel.split("/")
    for length in range(len(parts), 0, -1):
        old = "/".join(parts[:length])
        if old in mapping:
            return root / mapping[old] / "/".join(parts[length:])
    return p


class Path(type(NativePath())):
    """Path used by maintained tools to read unchanged historical references."""
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls, resolve_legacy(NativePath(*args)), **kwargs)

    def __init__(self, *args, **kwargs):
        if sys.version_info >= (3, 12):
            super().__init__(resolve_legacy(NativePath(*args)), **kwargs)

    def __truediv__(self, other):
        return Path(resolve_legacy(NativePath(self) / other))

    def joinpath(self, *parts):
        return Path(resolve_legacy(NativePath(self).joinpath(*parts)))
