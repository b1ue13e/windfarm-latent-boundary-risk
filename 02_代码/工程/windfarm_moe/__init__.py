from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS = {
    "analyze_gates": ("analysis", "analyze_gates"),
    "CacheBundle": ("data", "CacheBundle"),
    "DataConfig": ("config", "DataConfig"),
    "ERA5_FEATURE_NAMES": ("config", "ERA5_FEATURE_NAMES"),
    "EvalConfig": ("config", "EvalConfig"),
    "FEATURE_INDEX": ("config", "FEATURE_INDEX"),
    "FEATURE_NAMES": ("config", "FEATURE_NAMES"),
    "ModelConfig": ("config", "ModelConfig"),
    "REGIME_NAMES": ("config", "REGIME_NAMES"),
    "RegimeAwareForecaster": ("model", "RegimeAwareForecaster"),
    "RegimeWindowDataset": ("data", "RegimeWindowDataset"),
    "TrainConfig": ("config", "TrainConfig"),
    "WTB_FEATURE_NAMES": ("config", "WTB_FEATURE_NAMES"),
    "ensure_cache_ready": ("data", "ensure_cache_ready"),
    "load_cache_bundle": ("data", "load_cache_bundle"),
    "preprocess_dataset": ("preprocess", "preprocess_dataset"),
}


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = _EXPORTS[name]
    module = import_module(f".{module_name}", __name__)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


__all__ = sorted(_EXPORTS)
