from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import csv
import hashlib
import io
import json
import math
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import zipfile

import numpy as np
import pandas as pd

from .config import DataConfig, WTB_FEATURE_NAMES
from .graph import build_static_candidates
from .regimes import WTB_PRIMARY_NAMES, compute_wtb_operation_regime, inverse_frequency_weights_from_labels
from .utils import ensure_dir, fill_with_train_mean, load_json, save_json, standardize, wrap_degrees


EXTERNAL_FARMS = ("kelmarsh", "penmanshiel")
EXTERNAL_SPLITS = ("chronological", "leave-one-farm-out")
EXTERNAL_SOURCE_URLS = {
    "kelmarsh": "https://zenodo.org/records/16807551",
    "penmanshiel": "https://zenodo.org/records/16807304",
}
EXTERNAL_ZENODO_RECORDS = {
    "kelmarsh": "16807551",
    "penmanshiel": "16807304",
}
EXTERNAL_LICENSE = "CC-BY-4.0"
EXTERNAL_MAIN_VARIANTS = ("full",)
EXTERNAL_STRONG_BASELINE_VARIANTS = ("graph_wavenet", "patchtst")
EXTERNAL_BOUNDARY_ROUTER_VARIANTS = ("bal_align_force",)
EXTERNAL_REQUIRED_MODELS = (
    "Graph WaveNet",
    "PatchTST",
    "Physics-Aligned MoE",
    "MoE + L_bal + L_align + L_force",
)
EXTERNAL_ROUTING_REQUIRED_MODELS = (
    "Physics-Aligned MoE",
    "MoE + L_bal + L_align + L_force",
)
EXTERNAL_FULL_SOURCE_MIN_FILES = 31
EXTERNAL_FULL_SOURCE_MIN_BYTES = 10_000_000_000
EXTERNAL_STATIC_NOTES = {
    "kelmarsh": "6 Senvion MM92 turbines; 10-minute SCADA/static data from 2016 to end-2024.",
    "penmanshiel": "14 Senvion MM82 turbines; 10-minute SCADA/static data from 2016 to end-2024.",
}
EXTERNAL_FEATURE_NAMES = WTB_FEATURE_NAMES
EXTERNAL_PHYSICS_NAMES = ("Wspd", "Pab_mean", "wake_score", "Patv")


@dataclass(frozen=True)
class ExternalWindConfig:
    root_dir: Path = Path(".")
    cache_root: str = "artifacts/cache_external_wind"
    farm: str = "kelmarsh"
    split: str = "chronological"
    source_dir: Path | None = None
    target_farm: str = ""
    hist_len: int = 36
    pred_len: int = 24
    train_days: int = 180
    val_days: int = 30
    test_days: int = 35
    rated_wind: float = 10.5
    pitch_threshold: float = 2.0
    cut_in_wind: float = 3.0
    candidate_k: int = 8
    max_distance: float = 1500.0

    def normalized_farm(self) -> str:
        return _normalize_farm(self.farm)

    def normalized_target_farm(self) -> str:
        if self.target_farm:
            return _normalize_farm(self.target_farm)
        return "penmanshiel" if self.normalized_farm() == "kelmarsh" else "kelmarsh"

    def normalized_split(self) -> str:
        split = str(self.split).strip().lower().replace("_", "-")
        if split in {"leave-one-farm-out", "lofo"}:
            return "leave-one-farm-out"
        if split == "chronological":
            return split
        raise ValueError(f"Unsupported external wind split: {self.split}")

    def source_root(self) -> Path:
        if self.source_dir is not None:
            return Path(self.source_dir)
        return Path(self.root_dir) / "data" / "external_wind"

    def cache_dir(self) -> Path:
        split = self.normalized_split().replace("-", "_")
        if self.normalized_split() == "leave-one-farm-out":
            suffix = f"external_wind_{self.normalized_farm()}_to_{self.normalized_target_farm()}_{split}"
        else:
            suffix = f"external_wind_{self.normalized_farm()}_{split}"
        return Path(self.root_dir) / self.cache_root / suffix

    @classmethod
    def from_data_config(
        cls,
        config: DataConfig,
        farm: str | None = None,
        split: str | None = None,
        source_dir: str | Path | None = None,
        target_farm: str = "",
    ) -> "ExternalWindConfig":
        return cls(
            root_dir=Path(config.root_dir),
            cache_root=config.cache_root,
            farm=farm or config.external_farm,
            split=split or config.external_split,
            source_dir=Path(source_dir) if source_dir else (Path(config.external_source_dir) if config.external_source_dir else None),
            target_farm=target_farm or config.external_target_farm,
            hist_len=config.hist_len,
            pred_len=config.pred_len,
            train_days=config.train_days,
            val_days=config.val_days,
            test_days=config.test_days,
            rated_wind=config.external_rated_wind,
            pitch_threshold=config.external_pitch_threshold,
            cut_in_wind=config.external_cut_in_wind,
            candidate_k=config.era5_candidate_k,
        )


def _normalize_farm(value: str) -> str:
    farm = str(value).strip().lower().replace("_", "-")
    aliases = {
        "kelmarsh": "kelmarsh",
        "kelmarsh-wind-farm": "kelmarsh",
        "penmanshiel": "penmanshiel",
        "penmanshiel-wind-farm": "penmanshiel",
    }
    if farm not in aliases:
        raise ValueError(f"Unsupported external wind farm: {value}")
    return aliases[farm]


def _canonical_column(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(name).strip().lower())


def _find_column(columns: Iterable[str], candidates: Iterable[str], required: bool = True) -> str | None:
    normalized = {_canonical_column(column): column for column in columns}
    for candidate in candidates:
        key = _canonical_column(candidate)
        if key in normalized:
            return normalized[key]
    for candidate in candidates:
        key = _canonical_column(candidate)
        if not key or len(key) < 4:
            continue
        for column_key, column in normalized.items():
            if len(column_key) >= 4 and (key in column_key or column_key in key):
                return column
    if required:
        raise ValueError(f"Could not find required column. Tried: {', '.join(candidates)}")
    return None


def _find_turbine_id_column(columns: Iterable[str], required: bool = True) -> str | None:
    normalized = {_canonical_column(column): column for column in columns}
    exact_keys = [
        _canonical_column(name)
        for name in [
            "_source_turbine_id",
            "turbine_id",
            "turbine_name",
            "TurbineName",
            "asset_id",
            "Alternative Title",
            "Identity",
            "Turbine",
            "asset",
            "id",
        ]
    ]
    for key in exact_keys:
        if key in normalized:
            return normalized[key]
    for key, column in normalized.items():
        if "turbine" in key and not any(token in key for token in ["power", "reference", "setpoint", "potential"]):
            return column
    if required:
        raise ValueError("Could not find turbine id column and could not derive one from SCADA filenames.")
    return None


def _farm_dir(source_root: Path, farm: str) -> Path:
    direct = source_root / farm
    if direct.exists():
        return direct
    for path in source_root.iterdir() if source_root.exists() else []:
        if path.is_dir() and _canonical_column(path.name) == _canonical_column(farm):
            return path
    return direct


def _find_first_file(base_dir: Path, patterns: Iterable[str]) -> Path | None:
    if not base_dir.exists():
        return None
    for pattern in patterns:
        matches = sorted(base_dir.rglob(pattern))
        if matches:
            return matches[0]
    return None


def _scada_csv_paths(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    csvs = sorted(base_dir.rglob("*.csv"))
    preferred = [
        path
        for path in csvs
        if "scada" in path.name.lower()
        and not any(token in path.name.lower() for token in ["mapping", "static", "location", "coordinate"])
    ]
    if preferred:
        return preferred
    return [
        path
        for path in csvs
        if not any(token in path.name.lower() for token in ["mapping", "static", "location", "coordinate", "grid", "pmu"])
    ]


def _scada_zip_paths(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    return [
        path
        for path in sorted(base_dir.rglob("*.zip"))
        if "scada" in path.name.lower()
        and not any(token in path.name.lower() for token in ["mapping", "static", "grid", "pmu"])
    ]


def _external_static_paths(base_dir: Path) -> list[Path]:
    if not base_dir.exists():
        return []
    patterns = [
        "*turbine*static*.csv",
        "*static*.csv",
        "*location*.csv",
        "*coordinate*.csv",
        "*metadata*.csv",
    ]
    paths: set[Path] = set()
    for pattern in patterns:
        paths.update(path for path in base_dir.rglob(pattern) if path.is_file())
    return sorted(paths)


def _relative_source_path(path: Path, source_root: Path) -> str:
    try:
        return path.relative_to(source_root).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_file_fingerprint(path: Path, source_root: Path, farm: str, role: str, kind: str) -> dict[str, Any]:
    stat = path.stat()
    entry: dict[str, Any] = {
        "farm": farm,
        "role": role,
        "kind": kind,
        "path": _relative_source_path(path, source_root),
        "size": int(stat.st_size),
    }
    if path.suffix.lower() == ".zip":
        members: list[dict[str, Any]] = []
        with zipfile.ZipFile(path) as archive:
            for member in _scada_members(archive):
                info = archive.getinfo(member)
                members.append(
                    {
                        "name": member,
                        "file_size": int(info.file_size),
                        "compress_size": int(info.compress_size),
                        "crc": int(info.CRC),
                    }
                )
        entry["zip_member_count"] = int(len(members))
        entry["zip_members"] = members
    else:
        entry["sha256"] = _sha256_file(path)
    return entry


def _external_source_fingerprint(
    source_root: Path,
    role_farms: Iterable[tuple[str, str]],
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    for role, farm in role_farms:
        farm = _normalize_farm(farm)
        farm_dir = _farm_dir(source_root, farm)
        for path in _scada_csv_paths(farm_dir):
            entries.append(_source_file_fingerprint(path, source_root, farm, role, "scada_csv"))
        for path in _scada_zip_paths(farm_dir):
            entries.append(_source_file_fingerprint(path, source_root, farm, role, "scada_zip"))
        for path in _external_static_paths(farm_dir):
            entries.append(_source_file_fingerprint(path, source_root, farm, role, "static_metadata"))
    payload = {
        "version": 1,
        "files": sorted(entries, key=lambda item: (item["role"], item["farm"], item["path"], item["kind"])),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    payload["signature"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    payload["n_files"] = int(len(payload["files"]))
    payload["n_scada_files"] = int(sum(str(item.get("kind", "")).startswith("scada") for item in payload["files"]))
    payload["n_scada_zip_members"] = int(sum(int(item.get("zip_member_count", 0) or 0) for item in payload["files"]))
    return payload


def _source_roles_for_config(config: ExternalWindConfig) -> list[tuple[str, str]]:
    farm = config.normalized_farm()
    if config.normalized_split() == "leave-one-farm-out":
        return [("train", farm), ("test", config.normalized_target_farm())]
    return [("source", farm)]


def _derive_turbine_id_from_source(source: str) -> str:
    source_text = source.replace("\\", "/")
    if "!" in source_text:
        source_text = source_text.split("!", 1)[1]
    stem = Path(source_text).stem
    if re.search(r"WT[_\s-]?\d{1,2}\s*[-_]\s*\d{1,2}", stem, flags=re.IGNORECASE):
        return ""
    match = re.search(r"(KWF\d+|WT\d+|T\d+)", stem, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"(?:Penmanshiel|Kelmarsh)[_\s-]+(\d{1,2})(?:[_\s-]|$)", stem, flags=re.IGNORECASE)
        if match:
            return f"T{int(match.group(1)):02d}"
    return match.group(1).upper() if match else ""


def _greenbyte_header_from_sample(raw: bytes | str) -> tuple[list[str], int] | None:
    text = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    header_index = None
    header_line = ""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            candidate = stripped.lstrip("#").strip()
            if candidate.lower().startswith(("date and time", "timestamp", "time")) and "," in candidate:
                header_index = index
                header_line = candidate
                break
        elif "," in stripped:
            header_index = index
            header_line = stripped
            break
    if header_index is None or not header_line:
        return None
    columns = next(csv.reader([header_line]))
    return [str(column).strip() for column in columns], int(header_index)


def _external_scada_usecols(columns: Iterable[str]) -> list[int]:
    cols = list(columns)
    selected: list[str] = []

    def add(candidates: Iterable[str], required: bool = False) -> None:
        column = _find_column(cols, candidates, required=required)
        if column is not None and column not in selected:
            selected.append(column)

    add(["timestamp", "time_stamp", "start_time", "timestamp_start", "date and time", "time", "date_time", "datetime", "date"], True)
    turbine_column = _find_turbine_id_column(cols, required=False)
    if turbine_column is not None and turbine_column not in selected:
        selected.append(turbine_column)
    add(["wspd", "wind_speed", "windspeed", "wind speed", "wind speed ms", "wind speed m s", "avg wind speed"], True)
    add(["wdir", "wind_direction", "winddirection", "wind direction", "wind direction deg", "avg wind direction"])
    add(["ndir", "nacelle_direction", "nacelledirection", "yaw", "yaw angle", "nacelle position"])
    add(["patv", "power", "active_power", "activepower", "active power", "active power kw", "grid power"], True)
    add(["etmp", "environment_temperature", "ambient temperature", "nacelle ambient temperature", "outside temperature"])
    add(["itmp", "inside_temperature", "internal temperature", "nacelle temperature"])
    add(["prtv", "reactive_power", "reactive power"])
    for candidates in [
        [
            "pab1",
            "pitch_angle_1",
            "pitch1",
            "blade_pitch_angle_1",
            "pitch angle 1",
            "blade angle pitch position a",
            "blade angle (pitch position) a",
        ],
        [
            "pab2",
            "pitch_angle_2",
            "pitch2",
            "blade_pitch_angle_2",
            "pitch angle 2",
            "blade angle pitch position b",
            "blade angle (pitch position) b",
        ],
        [
            "pab3",
            "pitch_angle_3",
            "pitch3",
            "blade_pitch_angle_3",
            "pitch angle 3",
            "blade angle pitch position c",
            "blade angle (pitch position) c",
        ],
        ["pab", "pitch", "pitch_angle", "blade_pitch_angle", "pitch angle", "blade pitch"],
    ]:
        add(candidates)
    return [cols.index(column) for column in selected]


def _read_greenbyte_csv(
    source: Path | Any,
    nrows: int | None = None,
    relevant_columns_only: bool = False,
    chunksize: int | None = None,
) -> pd.DataFrame:
    if hasattr(source, "seek"):
        try:
            source.seek(0)
        except (OSError, AttributeError):
            pass
    sample = _read_csv_sample_bytes(source)
    header = _greenbyte_header_from_sample(sample)
    if header is None:
        text = sample.decode("utf-8-sig", errors="replace") if isinstance(sample, (bytes, bytearray)) else str(sample)
        return pd.read_csv(io.StringIO(text), nrows=nrows)
    columns, header_index = header
    usecols = _external_scada_usecols(columns) if relevant_columns_only else None
    read_kwargs = {
        "skiprows": header_index + 1,
        "names": columns,
        "header": None,
        "usecols": usecols,
        "nrows": nrows,
        "encoding": "utf-8-sig",
    }
    if chunksize is not None:
        read_kwargs["chunksize"] = int(chunksize)
    if hasattr(source, "seek"):
        try:
            source.seek(0)
        except (OSError, AttributeError):
            body = sample + source.read()
            return pd.read_csv(io.BytesIO(body), **read_kwargs)
        return pd.read_csv(source, **read_kwargs)
    return pd.read_csv(Path(source), **read_kwargs)


def _read_external_scada_member(source: Path | Any, source_name: str) -> pd.DataFrame:
    derived_id = _derive_turbine_id_from_source(source_name)
    chunks = _read_greenbyte_csv(source, relevant_columns_only=True, chunksize=250_000)
    frames: list[pd.DataFrame] = []
    iterator: Iterable[pd.DataFrame] = [chunks] if isinstance(chunks, pd.DataFrame) else chunks
    for df in iterator:
        if df.empty:
            continue
        key_columns = [
            column
            for column in [
                _find_column(df.columns, ["wspd", "wind_speed", "windspeed", "wind speed", "wind speed ms", "wind speed m s"], required=False),
                _find_column(df.columns, ["patv", "power", "active_power", "activepower", "active power", "active power kw"], required=False),
                _find_column(df.columns, ["blade angle pitch position a", "blade angle (pitch position) a", "pitch"], required=False),
            ]
            if column is not None
        ]
        if key_columns:
            numeric_keys = df[key_columns].apply(pd.to_numeric, errors="coerce")
            df = df.loc[numeric_keys.notna().any(axis=1)].copy()
        if df.empty:
            continue
        df["_source_file"] = source_name
        if derived_id:
            df["_source_turbine_id"] = derived_id
        prepared = _prepare_long_frame(df)
        if not prepared.empty:
            frames.append(prepared)
    if not frames:
        return pd.DataFrame()
    return _aggregate_long_frame(pd.concat(frames, ignore_index=True, sort=False))


def _read_csv_sample_bytes(source: Path | Any, max_bytes: int = 512 * 1024) -> bytes:
    if hasattr(source, "read"):
        chunks: list[bytes] = []
        remaining = int(max_bytes)
        while remaining > 0:
            chunk = source.read(min(64 * 1024, remaining))
            if not chunk:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            chunks.append(chunk)
            remaining -= len(chunk)
            if b"\n" in chunk and sum(part.count(b"\n") for part in chunks) > 20:
                break
        return b"".join(chunks)
    with Path(source).open("rb") as handle:
        return handle.read(int(max_bytes))


def _read_external_scada(base_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    source_files: list[str] = []
    for path in _scada_csv_paths(base_dir):
        df = _read_external_scada_member(path, str(path))
        if df.empty:
            continue
        frames.append(df)
        source_files.append(str(path))
    for path in _scada_zip_paths(base_dir):
        with zipfile.ZipFile(path) as archive:
            members = _scada_members(archive)
            for member in sorted(members):
                source_name = f"{path}!{member}"
                with archive.open(member) as handle:
                    df = _read_external_scada_member(handle, source_name)
                if df.empty:
                    continue
                frames.append(df)
                source_files.append(source_name)
    if not frames:
        raise FileNotFoundError(f"No SCADA CSV or SCADA ZIP member found under {base_dir}")
    combined = _aggregate_long_frame(pd.concat(frames, ignore_index=True, sort=False))
    if combined.empty:
        raise ValueError(f"SCADA file(s) are empty under {base_dir}")
    combined.attrs["source_file"] = ";".join(source_files)
    return combined


def inspect_external_wind_sources(
    source_dir: Path | str,
    output_dir: Path | str,
    farms: Iterable[str] | str = EXTERNAL_FARMS,
    max_members_per_zip: int = 3,
    sample_rows: int = 3,
) -> Path:
    output_dir = ensure_dir(output_dir)
    source_root = Path(source_dir)
    farm_list = [_normalize_farm(token) for token in _parse_csv_strings(farms)]
    rows: list[dict[str, Any]] = []
    for farm in farm_list:
        farm_dir = _farm_dir(source_root, farm)
        for path in _scada_csv_paths(farm_dir):
            rows.append(_inspect_csv_file(path, farm=farm, member="", sample_rows=sample_rows))
        for path in _scada_zip_paths(farm_dir):
            with zipfile.ZipFile(path) as archive:
                members = _scada_members(archive)
                for member in members[: max(0, int(max_members_per_zip))]:
                    rows.append(_inspect_zip_member(path, archive, member, farm=farm, sample_rows=sample_rows))
    frame = pd.DataFrame(rows)
    frame.to_csv(output_dir / "external_wind_scada_inspection.csv", index=False)
    save_json(
        output_dir / "external_wind_scada_inspection.json",
        {
            "kind": "external_wind_scada_inspection",
            "source_dir": str(source_root),
            "farms": farm_list,
            "max_members_per_zip": int(max_members_per_zip),
            "sample_rows": int(sample_rows),
            "n_sources": int(len(rows)),
            "columns_union": sorted({column for row in rows for column in str(row.get("columns", "")).split("|") if column}),
            "rows": rows,
        },
    )
    return output_dir


def _scada_members(archive: zipfile.ZipFile) -> list[str]:
    members = [
        name
        for name in archive.namelist()
        if name.lower().endswith(".csv")
        and ("scada" in name.lower() or "turbine_data" in name.lower())
        and "status" not in name.lower()
        and not any(token in name.lower() for token in ["mapping", "static", "location", "coordinate"])
    ]
    if not members:
        members = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
            and "status" not in name.lower()
            and not any(token in name.lower() for token in ["mapping", "static", "location", "coordinate"])
        ]
    return sorted(members)


def _inspect_csv_file(path: Path, farm: str, member: str, sample_rows: int) -> dict[str, Any]:
    frame = _read_greenbyte_csv(path, nrows=max(1, int(sample_rows)))
    return _inspection_row(path, farm=farm, member=member, frame=frame)


def _inspect_zip_member(
    path: Path,
    archive: zipfile.ZipFile,
    member: str,
    farm: str,
    sample_rows: int,
) -> dict[str, Any]:
    with archive.open(member) as handle:
        frame = _read_greenbyte_csv(handle, nrows=max(1, int(sample_rows)))
    return _inspection_row(path, farm=farm, member=member, frame=frame)


def _inspection_row(path: Path, farm: str, member: str, frame: pd.DataFrame) -> dict[str, Any]:
    source = f"{path}!{member}" if member else str(path)
    derived = _derive_turbine_id_from_source(source)
    return {
        "farm": farm,
        "archive": str(path),
        "member": member,
        "source": source,
        "derived_turbine_id": derived,
        "n_sample_rows": int(len(frame)),
        "n_columns": int(len(frame.columns)),
        "columns": "|".join(str(column) for column in frame.columns),
        "has_timestamp_candidate": bool(_find_column(frame.columns, ["timestamp", "time", "datetime", "date"], required=False)),
        "has_wind_speed_candidate": bool(_find_column(frame.columns, ["wind speed", "wspd", "windspeed"], required=False)),
        "has_power_candidate": bool(_find_column(frame.columns, ["power", "active power", "patv"], required=False)),
        "has_pitch_candidate": bool(
            _find_column(
                frame.columns,
                ["pitch", "blade angle pitch position a", "blade angle (pitch position) a", "pab"],
                required=False,
            )
        ),
    }


def _read_external_coords(base_dir: Path, node_ids: list[str]) -> pd.DataFrame:
    path = _find_first_file(
        base_dir,
        [
            "*turbine*static*.csv",
            "*static*.csv",
            "*location*.csv",
            "*coordinate*.csv",
            "*metadata*.csv",
        ],
    )
    if path is None:
        idx = np.arange(len(node_ids), dtype=np.float32)
        return pd.DataFrame({"node_id": node_ids, "x": idx * 500.0, "y": np.zeros_like(idx)})
    df = pd.read_csv(path)
    id_col = _find_column(
        df.columns,
        ["turbine_id", "Alternative Title", "alternative_title", "Turbine", "TurbineName", "Title", "asset_id", "Identity", "id"],
        required=False,
    )
    x_col = _find_column(df.columns, ["x", "easting", "longitude", "lon"], required=False)
    y_col = _find_column(df.columns, ["y", "northing", "latitude", "lat"], required=False)
    if id_col is None or x_col is None or y_col is None:
        idx = np.arange(len(node_ids), dtype=np.float32)
        return pd.DataFrame({"node_id": node_ids, "x": idx * 500.0, "y": np.zeros_like(idx)})
    coords = df[[id_col, x_col, y_col]].copy()
    coords.columns = ["node_id", "x", "y"]
    coords["node_id"] = coords["node_id"].astype(str)
    coords["x"] = pd.to_numeric(coords["x"], errors="coerce")
    coords["y"] = pd.to_numeric(coords["y"], errors="coerce")
    if _canonical_column(x_col) in {"longitude", "lon"} and _canonical_column(y_col) in {"latitude", "lat"}:
        lon = coords["x"].astype(float)
        lat = coords["y"].astype(float)
        lat0 = float(lat.mean()) if lat.notna().any() else 0.0
        coords["x"] = (lon - float(lon.mean())) * math.cos(math.radians(lat0)) * 111320.0
        coords["y"] = (lat - float(lat.mean())) * 110540.0
        coords["longitude"] = lon
        coords["latitude"] = lat
    return coords.dropna(subset=["x", "y"])


def _prepare_long_frame(raw: pd.DataFrame) -> pd.DataFrame:
    columns = list(raw.columns)
    time_col = _find_column(
        columns,
        ["timestamp", "time_stamp", "start_time", "timestamp_start", "date and time", "time", "date_time", "datetime", "date"],
        required=True,
    )
    turbine_col = _find_turbine_id_column(columns, required=False)
    if turbine_col is None:
        raise ValueError("Could not find turbine id column and could not derive one from SCADA filenames.")
    wspd_col = _find_column(
        columns,
        ["wspd", "wind_speed", "windspeed", "wind speed", "wind speed ms", "wind speed m s", "avg wind speed"],
        required=True,
    )
    wdir_col = _find_column(
        columns,
        ["wdir", "wind_direction", "winddirection", "wind direction", "wind direction deg", "avg wind direction"],
        required=False,
    )
    ndir_col = _find_column(
        columns,
        ["ndir", "nacelle_direction", "nacelledirection", "yaw", "yaw angle", "nacelle position"],
        required=False,
    )
    patv_col = _find_column(
        columns,
        ["patv", "power", "active_power", "activepower", "active power", "active power kw", "grid power"],
        required=True,
    )
    pab_cols = [
        column
        for column in [
            _find_column(
                columns,
                [
                    "pab1",
                    "pitch_angle_1",
                    "pitch1",
                    "blade_pitch_angle_1",
                    "pitch angle 1",
                    "blade angle pitch position a",
                    "blade angle (pitch position) a",
                ],
                required=False,
            ),
            _find_column(
                columns,
                [
                    "pab2",
                    "pitch_angle_2",
                    "pitch2",
                    "blade_pitch_angle_2",
                    "pitch angle 2",
                    "blade angle pitch position b",
                    "blade angle (pitch position) b",
                ],
                required=False,
            ),
            _find_column(
                columns,
                [
                    "pab3",
                    "pitch_angle_3",
                    "pitch3",
                    "blade_pitch_angle_3",
                    "pitch angle 3",
                    "blade angle pitch position c",
                    "blade angle (pitch position) c",
                ],
                required=False,
            ),
        ]
        if column is not None
    ]
    if not pab_cols:
        single_pitch = _find_column(
            columns,
            ["pab", "pitch", "pitch_angle", "blade_pitch_angle", "pitch angle", "blade pitch"],
            required=False,
        )
        if single_pitch is not None:
            pab_cols = [single_pitch]
    etmp_col = _find_column(columns, ["etmp", "external_temperature", "ambient_temperature", "ambient temperature", "temperature"], required=False)
    itmp_col = _find_column(columns, ["itmp", "internal_temperature", "nacelle_temperature"], required=False)
    prtv_col = _find_column(columns, ["prtv", "reactive_power", "reactivepower"], required=False)

    frame = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(raw[time_col], errors="coerce", utc=True).dt.tz_localize(None),
            "node_id": raw[turbine_col].astype(str),
            "Wspd": pd.to_numeric(raw[wspd_col], errors="coerce"),
            "Patv": pd.to_numeric(raw[patv_col], errors="coerce"),
        }
    )
    frame["Wdir"] = pd.to_numeric(raw[wdir_col], errors="coerce") if wdir_col else 0.0
    frame["Ndir"] = pd.to_numeric(raw[ndir_col], errors="coerce") if ndir_col else frame["Wdir"]
    frame["Etmp"] = pd.to_numeric(raw[etmp_col], errors="coerce") if etmp_col else 0.0
    frame["Itmp"] = pd.to_numeric(raw[itmp_col], errors="coerce") if itmp_col else 0.0
    frame["Prtv"] = pd.to_numeric(raw[prtv_col], errors="coerce") if prtv_col else 0.0
    if pab_cols:
        pab_values = raw[pab_cols].apply(pd.to_numeric, errors="coerce")
        frame["Pab_mean"] = pab_values.mean(axis=1)
        frame["Pab_std"] = pab_values.std(axis=1).fillna(0.0)
    else:
        frame["Pab_mean"] = np.nan
        frame["Pab_std"] = np.nan
    frame = frame.dropna(subset=["timestamp", "node_id"]).sort_values(["timestamp", "node_id"])
    if frame.empty:
        raise ValueError("External wind SCADA has no valid timestamp/turbine rows.")
    return _aggregate_long_frame(frame)


def _aggregate_long_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    value_cols = ["Wspd", "Patv", "Wdir", "Ndir", "Etmp", "Itmp", "Prtv", "Pab_mean", "Pab_std"]
    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
    frame["node_id"] = frame["node_id"].astype(str)
    for column in value_cols:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        else:
            frame[column] = np.nan
    frame = frame.dropna(subset=["timestamp", "node_id"])
    if frame.empty:
        return frame
    return (
        frame.groupby(["timestamp", "node_id"], sort=True, as_index=False)[value_cols]
        .mean()
        .sort_values(["timestamp", "node_id"])
        .reset_index(drop=True)
    )


def _regular_tensor(frame: pd.DataFrame, node_ids: list[str]) -> tuple[pd.DatetimeIndex, dict[str, np.ndarray]]:
    timestamps = pd.date_range(frame["timestamp"].min(), frame["timestamp"].max(), freq="10min")
    node_index = {node_id: idx for idx, node_id in enumerate(node_ids)}
    time_index = {timestamp: idx for idx, timestamp in enumerate(timestamps)}
    channels = ["Wspd", "Wdir", "Ndir", "Etmp", "Itmp", "Pab_mean", "Pab_std", "Prtv", "Patv"]
    arrays = {name: np.full((len(timestamps), len(node_ids)), np.nan, dtype=np.float32) for name in channels}
    for row in frame.itertuples(index=False):
        t_idx = time_index.get(row.timestamp)
        n_idx = node_index.get(str(row.node_id))
        if t_idx is None or n_idx is None:
            continue
        for name in channels:
            arrays[name][t_idx, n_idx] = np.float32(getattr(row, name))
    return timestamps, arrays


def _split_bounds(num_steps: int, train_days: int, val_days: int, test_days: int, steps_per_day: int = 144) -> dict[str, list[int]]:
    requested = [int(train_days) * steps_per_day, int(val_days) * steps_per_day, int(test_days) * steps_per_day]
    if sum(requested) <= num_steps and all(value > 0 for value in requested):
        train, val, test = requested
    else:
        train = max(1, int(round(num_steps * 0.6)))
        val = max(1, int(round(num_steps * 0.2)))
        if train + val >= num_steps:
            val = max(1, num_steps - train - 1)
        test = max(0, num_steps - train - val)
    train_end = min(train, num_steps)
    val_end = min(train_end + val, num_steps)
    test_end = min(val_end + test, num_steps)
    return {"train": [0, train_end], "val": [train_end, val_end], "test": [val_end, test_end]}


def _static_edges(num_steps: int, coords: np.ndarray, candidate_k: int, max_distance: float) -> tuple[np.ndarray, np.ndarray]:
    candidates = build_static_candidates(coords, candidate_k=candidate_k, max_distance=max_distance)
    edge_index = np.full((num_steps, coords.shape[0], candidate_k), -1, dtype=np.int16)
    edge_weight = np.zeros((num_steps, coords.shape[0], candidate_k), dtype=np.float32)
    src = np.asarray(candidates["src"], dtype=np.int16)
    dst = np.asarray(candidates["dst"], dtype=np.int16)
    dist = np.asarray(candidates["dist"], dtype=np.float32)
    for node in range(coords.shape[0]):
        incoming = np.where(dst == node)[0][:candidate_k]
        for slot, edge_id in enumerate(incoming):
            edge_index[:, node, slot] = int(src[edge_id])
            edge_weight[:, node, slot] = float(math.exp(-float(dist[edge_id]) / max(max_distance, 1.0)))
    return edge_index, edge_weight


def _standardize_feature_stack(
    raw_channels: dict[str, np.ndarray],
    train_stop: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], dict[str, np.ndarray]]:
    feature_arrays: list[np.ndarray] = []
    masks: list[np.ndarray] = []
    stats: dict[str, Any] = {}
    filled: dict[str, np.ndarray] = {}
    for feature_name in EXTERNAL_FEATURE_NAMES:
        values = raw_channels[feature_name]
        mask = np.isfinite(values).astype(np.float32)
        fill_values, fill_mean = fill_with_train_mean(values, train_stop)
        normalized, mean, std = standardize(fill_values, train_stop)
        feature_arrays.append(normalized)
        masks.append(mask)
        filled[feature_name] = fill_values
        stats[feature_name] = {"fill_mean": fill_mean, "mean": mean, "std": std}
    return np.stack(feature_arrays, axis=-1).astype(np.float32), np.stack(masks, axis=-1).astype(np.float32), stats, filled


def _standardize_physics_stack(physics: np.ndarray, train_stop: int) -> tuple[np.ndarray, dict[str, Any]]:
    normalized = np.zeros_like(physics, dtype=np.float32)
    stats: dict[str, Any] = {}
    for idx in range(physics.shape[-1]):
        filled, fill_mean = fill_with_train_mean(physics[..., idx], train_stop)
        values, mean, std = standardize(filled, train_stop)
        normalized[..., idx] = values
        stats[str(idx)] = {"fill_mean": fill_mean, "mean": mean, "std": std}
    return normalized, stats


def _write_cache_from_frame(
    frame: pd.DataFrame,
    coords_df: pd.DataFrame,
    config: ExternalWindConfig,
    output_dir: Path,
    split_bounds_override: dict[str, list[int]] | None = None,
    source_fingerprint: dict[str, Any] | None = None,
    source_files: str = "",
) -> Path:
    output_dir = ensure_dir(output_dir)
    node_ids = sorted(frame["node_id"].astype(str).unique().tolist())
    timestamps, raw = _regular_tensor(frame, node_ids)
    coords = pd.DataFrame({"node_id": node_ids}).merge(coords_df, on="node_id", how="left")
    missing = coords["x"].isna() | coords["y"].isna()
    if missing.any():
        fallback_idx = np.arange(len(coords), dtype=np.float32)
        coords.loc[missing, "x"] = fallback_idx[missing.to_numpy()] * 500.0
        coords.loc[missing, "y"] = 0.0
    coord_arr = coords[["x", "y"]].to_numpy(dtype=np.float32)
    split_bounds = split_bounds_override or _split_bounds(len(timestamps), config.train_days, config.val_days, config.test_days)
    train_stop = int(split_bounds["train"][1])

    wdir_wrapped = wrap_degrees(raw["Wdir"])
    ndir_wrapped = wrap_degrees(raw["Ndir"])
    target = raw["Patv"].astype(np.float32)
    target_mask = (np.isfinite(target) & (target >= 0.0)).astype(np.float32)
    feature_channels = {
        "Wspd": raw["Wspd"],
        "Wdir_sin": np.where(np.isfinite(wdir_wrapped), np.sin(np.deg2rad(wdir_wrapped)), np.nan).astype(np.float32),
        "Wdir_cos": np.where(np.isfinite(wdir_wrapped), np.cos(np.deg2rad(wdir_wrapped)), np.nan).astype(np.float32),
        "Ndir_sin": np.where(np.isfinite(ndir_wrapped), np.sin(np.deg2rad(ndir_wrapped)), np.nan).astype(np.float32),
        "Ndir_cos": np.where(np.isfinite(ndir_wrapped), np.cos(np.deg2rad(ndir_wrapped)), np.nan).astype(np.float32),
        "Etmp": raw["Etmp"],
        "Itmp": raw["Itmp"],
        "Pab_mean": raw["Pab_mean"],
        "Pab_std": raw["Pab_std"],
        "Prtv": raw["Prtv"],
        "Patv_hist": np.where(target_mask > 0.0, target, np.nan).astype(np.float32),
    }
    features, feature_mask, feature_stats, filled = _standardize_feature_stack(feature_channels, train_stop)
    edge_index, edge_weight = _static_edges(len(timestamps), coord_arr, config.candidate_k, config.max_distance)
    wake_score = np.zeros_like(raw["Wspd"], dtype=np.float32)
    pab_for_regime = raw["Pab_mean"]
    pitch_proxy_used = bool(np.isfinite(pab_for_regime).sum() == 0 and np.isfinite(raw["Wspd"]).any())
    if pitch_proxy_used:
        pab_for_regime = np.where(raw["Wspd"] > float(config.rated_wind), float(config.pitch_threshold) + 1.0, 0.0).astype(
            np.float32
        )
    regime, valid = compute_wtb_operation_regime(
        raw["Wspd"],
        pab_for_regime,
        cut_in_wind=config.cut_in_wind,
        rated_wind=config.rated_wind,
        pitch_threshold=config.pitch_threshold,
    )
    anchor_observed = np.isfinite(raw["Wspd"]) & np.isfinite(pab_for_regime)
    regime = np.where(anchor_observed, regime, 3).astype(np.int16)
    valid = (valid.astype(bool) & anchor_observed).astype(np.float32)
    primary_class_weights = inverse_frequency_weights_from_labels(regime, valid, 3)
    pitch_binary = np.zeros_like(regime, dtype=np.int16)
    pitch_valid = ((regime == 1) | (regime == 2)).astype(np.float32)
    pitch_binary[regime == 2] = 1
    pitch_force_weights = inverse_frequency_weights_from_labels(pitch_binary, pitch_valid, 2)
    physics = np.stack(
        [
            filled["Wspd"],
            filled["Pab_mean"],
            wake_score,
            np.nan_to_num(target, nan=0.0).astype(np.float32),
        ],
        axis=-1,
    ).astype(np.float32)
    physics_model, physics_stats = _standardize_physics_stack(physics, train_stop)
    time_index = np.stack(
        [
            ((np.arange(len(timestamps), dtype=np.int32) // 144) + 1),
            (np.arange(len(timestamps), dtype=np.int32) % 144),
        ],
        axis=-1,
    )
    anchor_index = np.arange(len(timestamps), dtype=np.int64)
    arrays = {
        "features": features,
        "feature_mask": feature_mask,
        "target": target.astype(np.float32),
        "target_mask": target_mask.astype(np.float32),
        "regime_primary": regime.astype(np.int16),
        "regime_primary_valid": valid.astype(np.float32),
        "regime_valid": valid.astype(np.float32),
        "regime_aux": np.zeros_like(regime, dtype=np.int16),
        "regime_aux_valid": np.zeros_like(valid, dtype=np.float32),
        "physics": physics,
        "physics_model": physics_model,
        "edge_index": edge_index.astype(np.int16),
        "edge_weight": edge_weight.astype(np.float32),
        "coords": coord_arr.astype(np.float32),
        "time_index": time_index,
        "anchor_index": anchor_index,
        "node_ids": np.arange(1, len(node_ids) + 1, dtype=np.int32),
    }
    for name, values in arrays.items():
        np.save(output_dir / f"{name}.npy", values)
    metadata = {
        "dataset": "external_wind",
        "farm": config.normalized_farm(),
        "target_farm": config.normalized_target_farm() if config.normalized_split() == "leave-one-farm-out" else "",
        "external_split": config.normalized_split(),
        "source_url": EXTERNAL_SOURCE_URLS.get(config.normalized_farm(), ""),
        "source_files": source_files,
        "external_source_fingerprint": source_fingerprint or {},
        "target_source_url": EXTERNAL_SOURCE_URLS.get(config.normalized_target_farm(), "")
        if config.normalized_split() == "leave-one-farm-out"
        else "",
        "license": EXTERNAL_LICENSE,
        "license_note": "Cubico/OpenOA Zenodo wind-farm SCADA released under CC-BY-4.0; cite the source record.",
        "source_static_note": EXTERNAL_STATIC_NOTES.get(config.normalized_farm(), ""),
        "target_static_note": EXTERNAL_STATIC_NOTES.get(config.normalized_target_farm(), "")
        if config.normalized_split() == "leave-one-farm-out"
        else "",
        "num_steps": int(len(timestamps)),
        "num_nodes": int(len(node_ids)),
        "node_labels": node_ids,
        "feature_names": list(EXTERNAL_FEATURE_NAMES),
        "physics_names": list(EXTERNAL_PHYSICS_NAMES),
        "primary_regime_names": list(WTB_PRIMARY_NAMES),
        "aux_regime_names": ["non_wake", "wake"],
        "primary_num_classes": 3,
        "wake_expert_index": 3,
        "steps_per_hour": 6,
        "split_bounds": split_bounds,
        "split_farm_roles": _split_farm_roles(
            config.normalized_split(),
            config.normalized_farm(),
            config.normalized_target_farm() if config.normalized_split() == "leave-one-farm-out" else "",
        ),
        "hist_len": config.hist_len,
        "pred_len": config.pred_len,
        "feature_stats": feature_stats,
        "physics_model_stats": physics_stats,
        "pitch_proxy_used_for_regime": pitch_proxy_used,
        "pitch_observed_fraction": float(np.isfinite(raw["Pab_mean"]).mean()),
        "primary_class_weights": primary_class_weights,
        "pitch_force_weights": pitch_force_weights,
        "wake_pos_weight": 1.0,
        "wake_threshold": 0.0,
        "wtb_thresholds": {
            "cut_in_wind": float(config.cut_in_wind),
            "rated_wind": float(config.rated_wind),
            "pitch_threshold": float(config.pitch_threshold),
        },
    }
    save_json(output_dir / "metadata.json", metadata)
    return output_dir


def _split_farm_roles(split: str, farm: str, target_farm: str = "") -> dict[str, list[str]]:
    if split == "leave-one-farm-out":
        return {"train": [farm], "val": [farm], "test": [target_farm]}
    return {"train": [farm], "val": [farm], "test": [farm]}


def _external_cache_metadata_complete(
    metadata_path: Path,
    farm: str,
    split: str,
    target_farm: str = "",
    source_fingerprint: dict[str, Any] | None = None,
) -> bool:
    if not metadata_path.exists():
        return False
    try:
        metadata = load_json(metadata_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    expected_target = target_farm if split == "leave-one-farm-out" else ""
    fingerprint_ok = True
    if source_fingerprint is not None:
        fingerprint_ok = (
            metadata.get("external_source_fingerprint", {}).get("signature")
            == source_fingerprint.get("signature")
        )
    return (
        metadata.get("dataset") == "external_wind"
        and metadata.get("farm") == farm
        and metadata.get("target_farm", "") == expected_target
        and metadata.get("external_split") == split
        and metadata.get("split_farm_roles") == _split_farm_roles(split, farm, expected_target)
        and fingerprint_ok
    )


def preprocess_external_wind(config: ExternalWindConfig) -> Path:
    farm = config.normalized_farm()
    split = config.normalized_split()
    cache_dir = config.cache_dir()
    source_root = config.source_root()
    source_fingerprint = _external_source_fingerprint(source_root, _source_roles_for_config(config))
    source_fingerprint_for_cache = source_fingerprint if source_fingerprint.get("n_scada_files", 0) else None
    required = [
        "metadata.json",
        "features.npy",
        "physics.npy",
        "physics_model.npy",
        "regime_primary.npy",
        "regime_primary_valid.npy",
        "regime_valid.npy",
        "anchor_index.npy",
    ]
    if all((cache_dir / name).exists() for name in required) and _external_cache_metadata_complete(
        cache_dir / "metadata.json",
        farm=farm,
        split=split,
        target_farm=config.normalized_target_farm() if split == "leave-one-farm-out" else "",
        source_fingerprint=source_fingerprint_for_cache,
    ):
        return cache_dir

    if split == "leave-one-farm-out" and _write_leave_one_farm_cache_from_chronological(
        config,
        cache_dir=cache_dir,
        source_fingerprint=source_fingerprint,
    ):
        return cache_dir

    farm_dir = _farm_dir(source_root, farm)
    raw = _read_external_scada(farm_dir)
    source_files = str(raw.attrs.get("source_file", ""))
    frame = raw
    coords = _read_external_coords(farm_dir, sorted(frame["node_id"].astype(str).unique().tolist()))
    split_override = None
    if split == "leave-one-farm-out":
        target_dir = _farm_dir(source_root, config.normalized_target_farm())
        target_raw = _read_external_scada(target_dir)
        target_source_files = str(target_raw.attrs.get("source_file", ""))
        source_files = ";".join(item for item in [source_files, target_source_files] if item)
        target_frame = target_raw
        target_coords = _read_external_coords(target_dir, sorted(target_frame["node_id"].astype(str).unique().tolist()))
        frame, coords, split_override = _build_leave_one_farm_frame(
            source_frame=frame,
            source_coords=coords,
            source_farm=farm,
            target_frame=target_frame,
            target_coords=target_coords,
            target_farm=config.normalized_target_farm(),
            train_steps=int(config.train_days) * 144,
            val_steps=int(config.val_days) * 144,
            test_steps=int(config.test_days) * 144,
        )
    return _write_cache_from_frame(
        frame,
        coords,
        config,
        cache_dir,
        split_bounds_override=split_override,
        source_fingerprint=source_fingerprint,
        source_files=source_files,
    )


def _prefix_frame_and_coords(
    frame: pd.DataFrame,
    coords: pd.DataFrame,
    farm: str,
    x_offset: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    out_frame = frame.copy()
    out_frame["node_id"] = farm + ":" + out_frame["node_id"].astype(str)
    out_coords = coords.copy()
    out_coords["node_id"] = farm + ":" + out_coords["node_id"].astype(str)
    out_coords["x"] = pd.to_numeric(out_coords["x"], errors="coerce") + float(x_offset)
    out_coords["y"] = pd.to_numeric(out_coords["y"], errors="coerce")
    return out_frame, out_coords


def _compact_frame_timestamps(frame: pd.DataFrame, start: pd.Timestamp) -> tuple[pd.DataFrame, pd.Timestamp, int]:
    out = frame.copy()
    unique_times = sorted(pd.to_datetime(out["timestamp"]).dropna().unique())
    mapping = {timestamp: start + pd.Timedelta(minutes=10 * idx) for idx, timestamp in enumerate(unique_times)}
    out["timestamp"] = pd.to_datetime(out["timestamp"]).map(mapping)
    next_start = start + pd.Timedelta(minutes=10 * len(unique_times))
    return out, next_start, len(unique_times)


def _window_frame_by_steps(frame: pd.DataFrame, max_steps: int) -> pd.DataFrame:
    max_steps = int(max_steps)
    if max_steps <= 0 or frame.empty:
        return frame.iloc[0:0].copy()
    unique_times = sorted(pd.to_datetime(frame["timestamp"]).dropna().unique())
    keep_times = set(unique_times[:max_steps])
    return frame[pd.to_datetime(frame["timestamp"]).isin(keep_times)].copy()


def _chronological_config(config: ExternalWindConfig, farm: str) -> ExternalWindConfig:
    return ExternalWindConfig(
        root_dir=config.root_dir,
        cache_root=config.cache_root,
        farm=farm,
        split="chronological",
        source_dir=config.source_dir,
        target_farm="",
        hist_len=config.hist_len,
        pred_len=config.pred_len,
        train_days=config.train_days,
        val_days=config.val_days,
        test_days=config.test_days,
        rated_wind=config.rated_wind,
        pitch_threshold=config.pitch_threshold,
        cut_in_wind=config.cut_in_wind,
        candidate_k=config.candidate_k,
        max_distance=config.max_distance,
    )


def _chronological_cache_complete(config: ExternalWindConfig, farm: str) -> bool:
    chrono = _chronological_config(config, farm)
    cache = chrono.cache_dir()
    required = [
        "metadata.json",
        "features.npy",
        "feature_mask.npy",
        "target.npy",
        "target_mask.npy",
        "physics.npy",
        "physics_model.npy",
        "regime_primary.npy",
        "regime_primary_valid.npy",
        "regime_valid.npy",
        "regime_aux.npy",
        "regime_aux_valid.npy",
        "coords.npy",
        "node_ids.npy",
    ]
    if not all((cache / name).exists() for name in required):
        return False
    fingerprint = _external_source_fingerprint(chrono.source_root(), [("source", farm)])
    return _external_cache_metadata_complete(
        cache / "metadata.json",
        farm=_normalize_farm(farm),
        split="chronological",
        target_farm="",
        source_fingerprint=fingerprint,
    )


def _stat_value(stats: dict[str, Any], feature: str, key: str, fallback: float) -> float:
    value = stats.get(feature, {}).get(key, fallback)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _retarget_features_to_source_stats(
    features: np.ndarray,
    feature_mask: np.ndarray,
    target_stats: dict[str, Any],
    source_stats: dict[str, Any],
) -> np.ndarray:
    out = np.empty_like(features, dtype=np.float32)
    for idx, name in enumerate(EXTERNAL_FEATURE_NAMES):
        target_mean = _stat_value(target_stats, name, "mean", 0.0)
        target_std = max(_stat_value(target_stats, name, "std", 1.0), 1e-6)
        source_mean = _stat_value(source_stats, name, "mean", 0.0)
        source_std = max(_stat_value(source_stats, name, "std", 1.0), 1e-6)
        source_fill = _stat_value(source_stats, name, "fill_mean", source_mean)
        raw = features[..., idx].astype(np.float32) * target_std + target_mean
        raw = np.where(feature_mask[..., idx] > 0.0, raw, source_fill).astype(np.float32)
        out[..., idx] = ((raw - source_mean) / source_std).astype(np.float32)
    return out


def _retarget_physics_model_to_source_stats(
    physics: np.ndarray,
    feature_mask: np.ndarray,
    source_stats: dict[str, Any],
) -> np.ndarray:
    raw = np.array(physics, dtype=np.float32, copy=True)
    if raw.shape[-1] >= 2 and len(EXTERNAL_FEATURE_NAMES) >= 8:
        wspd_fill = _stat_value(source_stats, "0", "fill_mean", _stat_value(source_stats, "0", "mean", 0.0))
        pab_fill = _stat_value(source_stats, "1", "fill_mean", _stat_value(source_stats, "1", "mean", 0.0))
        raw[..., 0] = np.where(feature_mask[..., 0] > 0.0, raw[..., 0], wspd_fill)
        raw[..., 1] = np.where(feature_mask[..., 7] > 0.0, raw[..., 1], pab_fill)
    out = np.empty_like(raw, dtype=np.float32)
    for idx in range(raw.shape[-1]):
        key = str(idx)
        mean = _stat_value(source_stats, key, "mean", 0.0)
        std = max(_stat_value(source_stats, key, "std", 1.0), 1e-6)
        out[..., idx] = ((raw[..., idx] - mean) / std).astype(np.float32)
    return out


def _pad_time_window(
    array: np.ndarray,
    start: int,
    end: int,
    node_offset: int,
    total_nodes: int,
    fill_value: float | int,
) -> np.ndarray:
    window = np.asarray(array[start:end])
    shape = (window.shape[0], total_nodes, *window.shape[2:])
    out = np.full(shape, fill_value, dtype=window.dtype)
    out[:, node_offset : node_offset + window.shape[1], ...] = window
    return out


def _write_leave_one_farm_cache_from_chronological(
    config: ExternalWindConfig,
    cache_dir: Path,
    source_fingerprint: dict[str, Any],
) -> bool:
    source_farm = config.normalized_farm()
    target_farm = config.normalized_target_farm()
    if not (_chronological_cache_complete(config, source_farm) and _chronological_cache_complete(config, target_farm)):
        return False
    source_cache = _chronological_config(config, source_farm).cache_dir()
    target_cache = _chronological_config(config, target_farm).cache_dir()
    source_meta = load_json(source_cache / "metadata.json")
    target_meta = load_json(target_cache / "metadata.json")
    train_steps = int(config.train_days) * 144
    val_steps = int(config.val_days) * 144
    test_steps = int(config.test_days) * 144
    source_end = train_steps + val_steps
    target_end = test_steps
    source_nodes = int(source_meta.get("num_nodes", np.load(source_cache / "features.npy", mmap_mode="r").shape[1]))
    target_nodes = int(target_meta.get("num_nodes", np.load(target_cache / "features.npy", mmap_mode="r").shape[1]))
    total_nodes = source_nodes + target_nodes
    output_dir = ensure_dir(cache_dir)

    source_features = np.load(source_cache / "features.npy", mmap_mode="r")[:source_end]
    source_feature_mask = np.load(source_cache / "feature_mask.npy", mmap_mode="r")[:source_end]
    target_feature_mask = np.load(target_cache / "feature_mask.npy", mmap_mode="r")[:target_end]
    target_features = _retarget_features_to_source_stats(
        np.load(target_cache / "features.npy", mmap_mode="r")[:target_end],
        target_feature_mask,
        target_meta.get("feature_stats", {}),
        source_meta.get("feature_stats", {}),
    )
    features = np.concatenate(
        [
            _pad_time_window(source_features, 0, source_end, 0, total_nodes, 0.0),
            _pad_time_window(target_features, 0, target_end, source_nodes, total_nodes, 0.0),
        ],
        axis=0,
    ).astype(np.float32)
    feature_mask = np.concatenate(
        [
            _pad_time_window(source_feature_mask, 0, source_end, 0, total_nodes, 0.0),
            _pad_time_window(target_feature_mask, 0, target_end, source_nodes, total_nodes, 0.0),
        ],
        axis=0,
    ).astype(np.float32)

    def concat_padded(name: str, fill_value: float | int) -> np.ndarray:
        source_arr = np.load(source_cache / f"{name}.npy", mmap_mode="r")
        target_arr = np.load(target_cache / f"{name}.npy", mmap_mode="r")
        return np.concatenate(
            [
                _pad_time_window(source_arr, 0, source_end, 0, total_nodes, fill_value),
                _pad_time_window(target_arr, 0, target_end, source_nodes, total_nodes, fill_value),
            ],
            axis=0,
        )

    target = concat_padded("target", 0.0).astype(np.float32)
    target_mask = concat_padded("target_mask", 0.0).astype(np.float32)
    regime_primary = concat_padded("regime_primary", 3).astype(np.int16)
    regime_primary_valid = concat_padded("regime_primary_valid", 0.0).astype(np.float32)
    regime_valid = concat_padded("regime_valid", 0.0).astype(np.float32)
    regime_aux = concat_padded("regime_aux", 0).astype(np.int16)
    regime_aux_valid = concat_padded("regime_aux_valid", 0.0).astype(np.float32)
    physics = concat_padded("physics", 0.0).astype(np.float32)
    source_physics_model = np.load(source_cache / "physics_model.npy", mmap_mode="r")[:source_end]
    target_physics_model = _retarget_physics_model_to_source_stats(
        np.load(target_cache / "physics.npy", mmap_mode="r")[:target_end],
        target_feature_mask,
        source_meta.get("physics_model_stats", {}),
    )
    physics_model = np.concatenate(
        [
            _pad_time_window(source_physics_model, 0, source_end, 0, total_nodes, 0.0),
            _pad_time_window(target_physics_model, 0, target_end, source_nodes, total_nodes, 0.0),
        ],
        axis=0,
    ).astype(np.float32)
    source_coords = np.asarray(np.load(source_cache / "coords.npy", mmap_mode="r"), dtype=np.float32)
    target_coords = np.asarray(np.load(target_cache / "coords.npy", mmap_mode="r"), dtype=np.float32).copy()
    target_coords[:, 0] += 100000.0
    coords = np.concatenate([source_coords, target_coords], axis=0).astype(np.float32)
    edge_index, edge_weight = _static_edges(features.shape[0], coords, config.candidate_k, config.max_distance)
    time_index = np.stack(
        [
            ((np.arange(features.shape[0], dtype=np.int32) // 144) + 1),
            (np.arange(features.shape[0], dtype=np.int32) % 144),
        ],
        axis=-1,
    )
    anchor_index = np.arange(features.shape[0], dtype=np.int64)
    node_ids = np.arange(1, total_nodes + 1, dtype=np.int32)
    arrays = {
        "features": features,
        "feature_mask": feature_mask,
        "target": target,
        "target_mask": target_mask,
        "regime_primary": regime_primary,
        "regime_primary_valid": regime_primary_valid,
        "regime_valid": regime_valid,
        "regime_aux": regime_aux,
        "regime_aux_valid": regime_aux_valid,
        "physics": physics,
        "physics_model": physics_model,
        "edge_index": edge_index.astype(np.int16),
        "edge_weight": edge_weight.astype(np.float32),
        "coords": coords,
        "time_index": time_index,
        "anchor_index": anchor_index,
        "node_ids": node_ids,
    }
    for name, values in arrays.items():
        np.save(output_dir / f"{name}.npy", values)
    source_labels = [f"{source_farm}:{label}" for label in source_meta.get("node_labels", [])]
    target_labels = [f"{target_farm}:{label}" for label in target_meta.get("node_labels", [])]
    split_bounds = {
        "train": [0, train_steps],
        "val": [train_steps, source_end],
        "test": [source_end, source_end + target_end],
    }
    metadata = dict(source_meta)
    metadata.update(
        {
            "dataset": "external_wind",
            "farm": source_farm,
            "target_farm": target_farm,
            "external_split": "leave-one-farm-out",
            "source_url": EXTERNAL_SOURCE_URLS.get(source_farm, ""),
            "target_source_url": EXTERNAL_SOURCE_URLS.get(target_farm, ""),
            "source_files": ";".join(
                item
                for item in [
                    str(source_meta.get("source_files", "")),
                    str(target_meta.get("source_files", "")),
                ]
                if item
            ),
            "external_source_fingerprint": source_fingerprint,
            "source_static_note": EXTERNAL_STATIC_NOTES.get(source_farm, ""),
            "target_static_note": EXTERNAL_STATIC_NOTES.get(target_farm, ""),
            "num_steps": int(features.shape[0]),
            "num_nodes": int(total_nodes),
            "node_labels": source_labels + target_labels,
            "split_bounds": split_bounds,
            "split_farm_roles": _split_farm_roles("leave-one-farm-out", source_farm, target_farm),
            "feature_stats": source_meta.get("feature_stats", {}),
            "physics_model_stats": source_meta.get("physics_model_stats", {}),
        }
    )
    save_json(output_dir / "metadata.json", metadata)
    return True


def _build_leave_one_farm_frame(
    source_frame: pd.DataFrame,
    source_coords: pd.DataFrame,
    source_farm: str,
    target_frame: pd.DataFrame,
    target_coords: pd.DataFrame,
    target_farm: str,
    train_steps: int,
    val_steps: int,
    test_steps: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, list[int]]]:
    source_frame = _window_frame_by_steps(source_frame, int(train_steps) + int(val_steps))
    target_frame = _window_frame_by_steps(target_frame, int(test_steps))
    source_frame, source_coords = _prefix_frame_and_coords(source_frame, source_coords, source_farm, x_offset=0.0)
    target_frame, target_coords = _prefix_frame_and_coords(target_frame, target_coords, target_farm, x_offset=100000.0)
    start = pd.Timestamp("2000-01-01 00:00:00")
    source_compact, next_start, source_steps = _compact_frame_timestamps(source_frame, start)
    target_compact, _, target_steps = _compact_frame_timestamps(target_frame, next_start)
    train_end = min(source_steps, max(1, int(train_steps)))
    val_end = min(source_steps, max(train_end + 1, train_end + int(val_steps)))
    test_end = source_steps + target_steps
    split_bounds = {
        "train": [0, train_end],
        "val": [train_end, val_end],
        "test": [source_steps, test_end],
    }
    frame = pd.concat([source_compact, target_compact], ignore_index=True)
    coords = pd.concat([source_coords, target_coords], ignore_index=True).drop_duplicates("node_id")
    return frame, coords, split_bounds


def write_external_wind_protocol(
    output_dir: Path | str,
    root_dir: Path | str = ".",
    source_dir: Path | str = "data/external_wind",
    cache_root: Path | str = "artifacts/cache_external_wind",
    seeds: Iterable[int] | str = (201, 202, 203, 204, 205),
    farms: Iterable[str] | str = EXTERNAL_FARMS,
    suite_dir: Path | str = "artifacts/external_wind_runs",
) -> Path:
    output_dir = ensure_dir(output_dir)
    seed_list = _parse_csv_ints(seeds)
    farm_list = [_normalize_farm(token) for token in _parse_csv_strings(farms)]
    commands: list[str] = []
    reviewer_pack_commands: list[str] = []
    protocols: list[dict[str, Any]] = []
    for farm in farm_list:
        other = "penmanshiel" if farm == "kelmarsh" else "kelmarsh"
        for split, target in [("chronological", ""), ("leave-one-farm-out", other)]:
            split_slug = split.replace("-", "_")
            target_arg = f"--external-target-farm {target} " if target else ""
            output_root = Path(suite_dir) / farm / split_slug
            if target:
                cache_dir = Path(cache_root) / f"external_wind_{farm}_to_{target}_{split.replace('-', '_')}"
                pack_root = Path(suite_dir).parent / "external_wind_reviewer_stats" / f"{farm}_to_{target}" / split_slug
            else:
                cache_dir = Path(cache_root) / f"external_wind_{farm}_{split.replace('-', '_')}"
                pack_root = Path(suite_dir).parent / "external_wind_reviewer_stats" / farm / split_slug
            commands.append(
                "python main.py external-wind-preprocess "
                f"--root-dir {root_dir} --external-source-dir {source_dir} --farm {farm} "
                f"--external-split {split} {target_arg}--cache-root {cache_root}"
            )
            commands.append(
                "python main.py paper-batch --dataset external_wind "
                f"--root-dir {root_dir} --external-source-dir {source_dir} --farm {farm} --external-split {split} "
                f"{target_arg}--cache-root {cache_root} --output-dir {output_root} "
                f"--groups main --variant-keys {','.join(EXTERNAL_MAIN_VARIANTS)} "
                f"--seeds {','.join(str(seed) for seed in seed_list)} "
                "--epochs 20 --batch-size 16 --hidden-dim 64 --skip-visuals"
            )
            commands.append(
                "python main.py paper-batch --dataset external_wind "
                f"--root-dir {root_dir} --external-source-dir {source_dir} --farm {farm} --external-split {split} "
                f"{target_arg}--cache-root {cache_root} --output-dir {output_root} "
                f"--groups ablation --variant-keys {','.join(EXTERNAL_BOUNDARY_ROUTER_VARIANTS)} "
                f"--seeds {','.join(str(seed) for seed in seed_list)} "
                "--epochs 20 --batch-size 16 --hidden-dim 64 --skip-visuals"
            )
            commands.append(
                "python main.py paper-batch --dataset external_wind "
                f"--root-dir {root_dir} --external-source-dir {source_dir} --farm {farm} --external-split {split} "
                f"{target_arg}--cache-root {cache_root} --output-dir {output_root} "
                f"--groups strong_baselines --variant-keys {','.join(EXTERNAL_STRONG_BASELINE_VARIANTS)} "
                f"--seeds {','.join(str(seed) for seed in seed_list)} --strong-baseline-seeds {','.join(str(seed) for seed in seed_list)} "
                "--epochs 20 --batch-size 16 --hidden-dim 64 --skip-visuals"
            )
            reviewer_pack_commands.append(
                "python main.py reviewer-stat-pack --dataset external_wind "
                f"--root-dir {root_dir} --output-dir {pack_root} --suite-dir {output_root} --cache-dir {cache_dir} "
                "--split test --models \"Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force\" "
                "--reference-model \"MoE + L_bal + L_align + L_force\" "
                "--baseline-models \"Graph WaveNet,PatchTST,Physics-Aligned MoE\" "
                "--bootstrap-samples 1000 --permutation-samples 1000 --max-per-example-rows 0 "
                "--max-paired-examples 100000 --top-k-failures 24"
            )
            reviewer_pack_commands.append(
                f"python main.py reviewer-stat-pack-guard --pack-dir {pack_root} --output-dir {pack_root}_guard "
                "--min-runs 20 --required-models \"Graph WaveNet,PatchTST,Physics-Aligned MoE,MoE + L_bal + L_align + L_force\" "
                f"--required-seeds {','.join(str(seed) for seed in seed_list)}"
            )
            protocols.append(
                {
                    "dataset": "external_wind",
                    "farm": farm,
                    "target_farm": target,
                    "split_id": split,
                    "seeds": seed_list,
                    "source_url": EXTERNAL_SOURCE_URLS[farm],
                    "target_source_url": EXTERNAL_SOURCE_URLS.get(target, ""),
                    "license": EXTERNAL_LICENSE,
                    "models": list(EXTERNAL_REQUIRED_MODELS),
                    "main_variants": list(EXTERNAL_MAIN_VARIANTS),
                    "strong_baseline_variants": list(EXTERNAL_STRONG_BASELINE_VARIANTS),
                    "boundary_router_variants": list(EXTERNAL_BOUNDARY_ROUTER_VARIANTS),
                    "reviewer_pack_dir": str(pack_root),
                }
            )
    (output_dir / "external_wind_commands.ps1").write_text("\n".join(commands) + "\n", encoding="utf-8")
    (output_dir / "external_wind_reviewer_pack_commands.ps1").write_text(
        "\n".join(reviewer_pack_commands) + "\n", encoding="utf-8"
    )
    save_json(
        output_dir / "external_wind_protocol.json",
        {
            "kind": "external_wind_protocol",
            "root_dir": str(root_dir),
            "source_dir": str(source_dir),
            "cache_root": str(cache_root),
            "suite_dir": str(suite_dir),
            "reviewer_pack_commands": str(output_dir / "external_wind_reviewer_pack_commands.ps1"),
            "protocols": protocols,
        },
    )
    return output_dir


def fetch_external_wind_sources(
    output_dir: Path | str,
    source_dir: Path | str = "data/external_wind",
    farms: Iterable[str] | str = EXTERNAL_FARMS,
    years: Iterable[int] | str | None = None,
    include_static: bool = True,
    include_scada: bool = True,
    include_mapping: bool = False,
    file_pattern: str = "",
    download: bool = False,
    overwrite: bool = False,
) -> Path:
    output_dir = ensure_dir(output_dir)
    source_root = ensure_dir(Path(source_dir))
    farm_list = [_normalize_farm(token) for token in _parse_csv_strings(farms)]
    year_set = set(_parse_csv_ints(years)) if years not in (None, "") else set()
    rows: list[dict[str, Any]] = []
    for farm in farm_list:
        record_id = EXTERNAL_ZENODO_RECORDS[farm]
        record = _zenodo_record(record_id)
        farm_dir = ensure_dir(source_root / farm)
        for file_info in record.get("files", []):
            key = str(file_info.get("key", ""))
            if file_pattern and file_pattern.lower() not in key.lower():
                continue
            if not _external_file_selected(
                key,
                year_set,
                include_static=include_static,
                include_scada=include_scada,
                include_mapping=include_mapping,
            ):
                continue
            local_path = farm_dir / key
            download_url = str((file_info.get("links") or {}).get("self", ""))
            status = "manifest_only"
            if local_path.exists() and not overwrite:
                status = "exists"
            elif download:
                if not download_url:
                    raise ValueError(f"Zenodo file {key} does not expose a download URL.")
                _download_file(download_url, local_path, expected_size=int(file_info.get("size", 0) or 0))
                status = "downloaded"
            checksum = str(file_info.get("checksum", ""))
            rows.append(
                {
                    "farm": farm,
                    "record_id": record_id,
                    "record_url": EXTERNAL_SOURCE_URLS[farm],
                    "api_url": f"https://zenodo.org/api/records/{record_id}",
                    "license": EXTERNAL_LICENSE,
                    "key": key,
                    "size": int(file_info.get("size", 0) or 0),
                    "checksum": checksum,
                    "download_url": download_url,
                    "local_path": str(local_path),
                    "selected_years": ",".join(str(year) for year in sorted(year_set)),
                    "download_requested": bool(download),
                    "status": status,
                    "local_exists": bool(local_path.exists()),
                    "local_md5": _md5_file(local_path) if local_path.exists() else "",
                    "checksum_match": _checksum_matches(local_path, checksum) if local_path.exists() else False,
                }
            )
    manifest_df = pd.DataFrame(rows)
    manifest_df.to_csv(output_dir / "external_wind_source_manifest.csv", index=False)
    save_json(
        output_dir / "external_wind_source_manifest.json",
        {
            "kind": "external_wind_source_manifest",
            "source_dir": str(source_root),
            "farms": farm_list,
            "years": sorted(year_set),
            "include_static": bool(include_static),
            "include_scada": bool(include_scada),
            "include_mapping": bool(include_mapping),
            "file_pattern": str(file_pattern),
            "download": bool(download),
            "license": EXTERNAL_LICENSE,
            "source_urls": EXTERNAL_SOURCE_URLS,
            "records": EXTERNAL_ZENODO_RECORDS,
            "n_files": int(len(rows)),
            "n_downloaded": int(sum(row["status"] == "downloaded" for row in rows)),
            "n_existing": int(sum(row["status"] == "exists" for row in rows)),
            "n_manifest_only": int(sum(row["status"] == "manifest_only" for row in rows)),
            "total_selected_bytes": int(sum(row["size"] for row in rows)),
        },
    )
    return output_dir


def run_external_wind_source_guard(
    output_dir: Path | str,
    manifest_path: Path | str = "artifacts/external_wind_full_manifest/external_wind_source_manifest.csv",
    farms: Iterable[str] | str = EXTERNAL_FARMS,
    min_files: int = EXTERNAL_FULL_SOURCE_MIN_FILES,
    min_total_bytes: int = EXTERNAL_FULL_SOURCE_MIN_BYTES,
) -> Path:
    output_dir = ensure_dir(output_dir)
    manifest_path = Path(manifest_path)
    required_farms = [_normalize_farm(token) for token in _parse_csv_strings(farms)]
    manifest_exists = manifest_path.exists()
    manifest_df = pd.read_csv(manifest_path) if manifest_exists else pd.DataFrame()
    status_df = manifest_df.copy()
    n_rows = int(len(manifest_df))
    size_values = pd.to_numeric(
        manifest_df.get("size", pd.Series([0] * n_rows, index=manifest_df.index)),
        errors="coerce",
    ).fillna(0)
    total_bytes = int(size_values.sum())
    farm_values = (
        set(manifest_df.get("farm", pd.Series(dtype=str)).astype(str).str.strip().str.lower())
        if n_rows
        else set()
    )
    local_exists = _manifest_bool_series(manifest_df, "local_exists")
    checksum_match = _manifest_bool_series(manifest_df, "checksum_match")
    if n_rows and "local_path" in manifest_df.columns:
        refreshed_exists: list[bool] = []
        refreshed_checksums: list[bool] = []
        for _, row in manifest_df.iterrows():
            path = Path(str(row.get("local_path", "")))
            exists = path.exists()
            refreshed_exists.append(bool(exists))
            refreshed_checksums.append(_checksum_matches(path, str(row.get("checksum", ""))) if exists else False)
        local_exists = pd.Series(refreshed_exists, index=manifest_df.index, dtype=bool)
        checksum_match = pd.Series(refreshed_checksums, index=manifest_df.index, dtype=bool)
    status_values = (
        manifest_df.get("status", pd.Series([""] * n_rows, index=manifest_df.index))
        .astype(str)
        .str.strip()
        .str.lower()
    )
    manifest_only = status_values.eq("manifest_only") & ~local_exists
    if n_rows:
        status_df["guard_local_exists"] = local_exists
        status_df["guard_checksum_match"] = checksum_match
        status_df["guard_manifest_only"] = manifest_only
    else:
        status_df = pd.DataFrame(
            columns=[
                "farm",
                "key",
                "size",
                "local_path",
                "status",
                "local_exists",
                "checksum_match",
                "guard_local_exists",
                "guard_checksum_match",
                "guard_manifest_only",
            ]
        )
    status_df.to_csv(output_dir / "external_wind_source_status.csv", index=False)

    json_manifest_path = manifest_path.with_suffix(".json")
    license_checks: list[bool] = []
    if n_rows and "license" in manifest_df.columns:
        license_checks.append(
            bool(manifest_df["license"].astype(str).str.strip().str.upper().eq(EXTERNAL_LICENSE).all())
        )
    if json_manifest_path.exists():
        try:
            license_checks.append(str(load_json(json_manifest_path).get("license", "")).strip().upper() == EXTERNAL_LICENSE)
        except (OSError, json.JSONDecodeError):
            license_checks.append(False)
    license_ok = bool(license_checks) and all(license_checks)
    path_text = " ".join(
        manifest_df.get(column, pd.Series(dtype=str)).astype(str).str.lower().str.cat(sep=" ")
        for column in ["local_path", "key", "record_url", "api_url"]
        if column in manifest_df.columns
    )
    external_source_tokens_ok = not any(token in path_text for token in ["sdwpf", "wtbdata", "kdd"])
    checks = {
        "manifest_exists": bool(manifest_exists),
        "manifest_has_rows": n_rows > 0,
        "status_column_present": "status" in manifest_df.columns,
        "required_farms_present": set(required_farms).issubset(farm_values),
        "file_count_meets_minimum": n_rows >= int(min_files),
        "total_selected_bytes_meets_minimum": total_bytes >= int(min_total_bytes),
        "all_selected_files_local_exists": n_rows > 0 and bool(local_exists.all()),
        "all_selected_files_checksum_match": n_rows > 0 and bool(checksum_match.all()),
        "no_manifest_only_rows": n_rows > 0 and not bool(manifest_only.any()),
        "license_is_cc_by_4": license_ok,
        "no_wtb_or_sdwpf_source": external_source_tokens_ok,
    }
    complete = all(checks.values())
    report = {
        "status": "complete_external_source_evidence" if complete else "blocked_external_source_incomplete",
        "claim_gate": "within_wtb_only" if complete else "blocked_not_citable",
        "checks": checks,
        "manifest_path": str(manifest_path),
        "json_manifest_path": str(json_manifest_path) if json_manifest_path.exists() else "",
        "required_farms": required_farms,
        "farms_present": sorted(farm_values),
        "min_files": int(min_files),
        "n_files": n_rows,
        "min_total_bytes": int(min_total_bytes),
        "total_selected_bytes": total_bytes,
        "n_local_exists": int(local_exists.sum()) if n_rows else 0,
        "n_checksum_match": int(checksum_match.sum()) if n_rows else 0,
        "n_manifest_only": int(manifest_only.sum()) if n_rows else 0,
        "missing_local_paths": _manifest_problem_paths(manifest_df, ~local_exists if n_rows else pd.Series(dtype=bool)),
        "checksum_failed_paths": _manifest_problem_paths(manifest_df, ~checksum_match if n_rows else pd.Series(dtype=bool)),
        "license": EXTERNAL_LICENSE,
        "source_urls": EXTERNAL_SOURCE_URLS,
    }
    save_json(output_dir / "external_wind_source_guard.json", report)
    return output_dir


def _zenodo_record(record_id: str) -> dict[str, Any]:
    with urlopen(f"https://zenodo.org/api/records/{record_id}", timeout=60) as handle:
        return json.loads(handle.read().decode("utf-8"))


def _external_file_selected(
    key: str,
    years: set[int],
    *,
    include_static: bool,
    include_scada: bool,
    include_mapping: bool,
) -> bool:
    lowered = key.lower()
    is_static = lowered.endswith(".csv") and "static" in lowered
    is_scada = "scada" in lowered and lowered.endswith(".zip")
    is_mapping = "datasignalmapping" in lowered or "signal_mapping" in lowered or "signalmapping" in lowered
    if is_static:
        return bool(include_static)
    if is_mapping:
        return bool(include_mapping)
    if not is_scada:
        return False
    if not include_scada:
        return False
    if not years:
        return True
    key_years = {int(match) for match in re.findall(r"20\d{2}|201\d", key)}
    return bool(key_years.intersection(years))


def _download_file(url: str, path: Path, expected_size: int | None = None, retries: int = 8) -> None:
    ensure_dir(path.parent)
    last_error: Exception | None = None
    for attempt in range(int(retries)):
        try:
            _download_file_once(url, path, expected_size=expected_size)
            return
        except (OSError, HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt + 1 >= int(retries):
                break
            time.sleep(min(2.0 * (2 ** attempt), 30.0))
    if last_error is not None:
        raise last_error


def _download_file_once(url: str, path: Path, expected_size: int | None = None) -> None:
    temp_path = path.with_suffix(path.suffix + ".part")
    expected = int(expected_size or 0)
    if temp_path.exists() and expected > 0 and temp_path.stat().st_size > expected:
        temp_path.unlink()
    partial_size = temp_path.stat().st_size if temp_path.exists() else 0
    if expected > 0 and partial_size == expected:
        temp_path.replace(path)
        return

    headers = {"Range": f"bytes={partial_size}-"} if partial_size > 0 else {}
    request = Request(url, headers=headers)
    with urlopen(request, timeout=120) as response:
        status_code = int(response.getcode() or getattr(response, "status", 200) or 200)
        mode = "ab" if partial_size > 0 and status_code == 206 else "wb"
        with temp_path.open(mode) as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
    if expected > 0 and temp_path.stat().st_size != expected:
        raise IOError(
            f"Incomplete download for {path}: expected {expected} bytes, got {temp_path.stat().st_size} bytes"
        )
    temp_path.replace(path)


def _md5_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checksum_matches(path: Path, checksum: str) -> bool:
    checksum = str(checksum)
    if not path.exists() or not checksum.startswith("md5:"):
        return False
    return _md5_file(path).lower() == checksum.split(":", 1)[1].lower()


def _manifest_bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    if column not in df.columns:
        return pd.Series([False] * len(df), index=df.index, dtype=bool)
    return df[column].astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def _manifest_problem_paths(df: pd.DataFrame, mask: pd.Series, limit: int = 20) -> list[str]:
    if df.empty or mask.empty:
        return []
    subset = df.loc[mask.reindex(df.index, fill_value=False)]
    if subset.empty:
        return []
    if "local_path" in subset.columns:
        values = subset["local_path"].astype(str).tolist()
    elif "key" in subset.columns:
        values = subset["key"].astype(str).tolist()
    else:
        values = [str(index) for index in subset.index.tolist()]
    return values[: int(limit)]


def run_external_wind_guard(
    output_dir: Path | str,
    cache_dirs: Iterable[Path | str] | str | None = None,
    suite_dir: Path | str = "artifacts/external_wind_runs",
    seeds: Iterable[int] | str = (201, 202, 203, 204, 205),
    required_models: Iterable[str] | str = EXTERNAL_REQUIRED_MODELS,
    min_nmi: float = 0.50,
    min_ari: float = 0.30,
) -> Path:
    output_dir = ensure_dir(output_dir)
    seed_list = _parse_csv_ints(seeds)
    cache_list = [Path(path) for path in _parse_csv_strings(cache_dirs or "")]
    cache_rows = [_cache_status(path) for path in cache_list]
    suite = Path(suite_dir)
    run_rows = _external_run_status(suite, seed_list, _parse_csv_strings(required_models))
    run_df = pd.DataFrame(run_rows)
    run_df.to_csv(output_dir / "external_wind_run_status.csv", index=False)
    cache_df = pd.DataFrame(cache_rows)
    cache_df.to_csv(output_dir / "external_wind_cache_status.csv", index=False)
    complete_runs = int(run_df["complete"].sum()) if not run_df.empty else 0
    expected_runs = int(len(run_df))
    nmi_values = pd.to_numeric(run_df.get("nmi"), errors="coerce").dropna() if "nmi" in run_df else pd.Series(dtype=float)
    ari_values = pd.to_numeric(run_df.get("ari"), errors="coerce").dropna() if "ari" in run_df else pd.Series(dtype=float)
    boundary_values = (
        pd.to_numeric(run_df.get("boundary_rmse"), errors="coerce").dropna()
        if "boundary_rmse" in run_df
        else pd.Series(dtype=float)
    )
    switch_values = (
        pd.to_numeric(run_df.get("switch_rmse"), errors="coerce").dropna()
        if "switch_rmse" in run_df
        else pd.Series(dtype=float)
    )
    overall_values = (
        pd.to_numeric(run_df.get("overall_rmse"), errors="coerce").dropna()
        if "overall_rmse" in run_df
        else pd.Series(dtype=float)
    )
    entropy_values = (
        pd.to_numeric(run_df.get("expert_usage_entropy"), errors="coerce").dropna()
        if "expert_usage_entropy" in run_df
        else pd.Series(dtype=float)
    )
    expert_usage_values = (
        run_df.get("expert_usage", pd.Series(dtype=str)).astype(str)
        if "expert_usage" in run_df
        else pd.Series(dtype=str)
    )
    expert_usage_present = expert_usage_values.map(_expert_usage_present)
    routing_model_set = set(EXTERNAL_ROUTING_REQUIRED_MODELS).intersection(set(_parse_csv_strings(required_models)))
    routing_df = (
        run_df[run_df.get("model", pd.Series(dtype=str)).astype(str).isin(routing_model_set)].copy()
        if not run_df.empty and routing_model_set
        else pd.DataFrame()
    )
    expected_routing_runs = int(len(routing_df))
    routing_nmi_values = (
        pd.to_numeric(routing_df.get("nmi"), errors="coerce").dropna()
        if not routing_df.empty and "nmi" in routing_df
        else pd.Series(dtype=float)
    )
    routing_ari_values = (
        pd.to_numeric(routing_df.get("ari"), errors="coerce").dropna()
        if not routing_df.empty and "ari" in routing_df
        else pd.Series(dtype=float)
    )
    routing_entropy_values = (
        pd.to_numeric(routing_df.get("expert_usage_entropy"), errors="coerce").dropna()
        if not routing_df.empty and "expert_usage_entropy" in routing_df
        else pd.Series(dtype=float)
    )
    routing_expert_usage_values = (
        routing_df.get("expert_usage", pd.Series(dtype=str)).astype(str)
        if not routing_df.empty and "expert_usage" in routing_df
        else pd.Series(dtype=str)
    )
    routing_expert_usage_present = routing_expert_usage_values.map(_expert_usage_present)
    forecast_metric_values_present = bool(
        expected_runs > 0
        and len(overall_values) == expected_runs
        and len(switch_values) == expected_runs
    )
    routing_metric_values_present = bool(
        expected_routing_runs > 0
        and len(routing_entropy_values) == expected_routing_runs
        and len(routing_expert_usage_values) == expected_routing_runs
        and bool(routing_expert_usage_present.all())
    )
    lofo = run_df[run_df.get("split_id", pd.Series(dtype=str)).astype(str).eq("leave-one-farm-out")].copy()
    chrono = run_df[run_df.get("split_id", pd.Series(dtype=str)).astype(str).eq("chronological")].copy()
    lofo_pairs = set(
        zip(
            lofo.get("farm", pd.Series(dtype=str)).astype(str),
            lofo.get("target_farm", pd.Series(dtype=str)).astype(str),
        )
    )
    required_lofo_pairs = {("kelmarsh", "penmanshiel"), ("penmanshiel", "kelmarsh")}
    chrono_farms = set(chrono.get("farm", pd.Series(dtype=str)).astype(str))
    checks = {
        "all_cache_dirs_exist": bool(cache_rows) and all(row["complete"] for row in cache_rows),
        "cache_dataset_is_external_wind": bool(cache_rows)
        and all(str(row.get("dataset", "")) == "external_wind" for row in cache_rows),
        "cache_license_is_cc_by_4": bool(cache_rows)
        and all(str(row.get("license", "")).upper() == EXTERNAL_LICENSE for row in cache_rows),
        "required_farms_cached": {"kelmarsh", "penmanshiel"}.issubset({str(row.get("farm", "")) for row in cache_rows}),
        "all_expected_runs_complete": expected_runs > 0 and complete_runs == expected_runs,
        "cross_farm_both_directions_complete": required_lofo_pairs.issubset(lofo_pairs)
        and bool(lofo.empty or lofo["complete"].all()),
        "chronological_sanity_complete": {"kelmarsh", "penmanshiel"}.issubset(chrono_farms)
        and bool(chrono.empty or chrono["complete"].all()),
        "all_required_metric_files_exist": expected_runs > 0 and bool(run_df.get("metric_files_complete", pd.Series(dtype=bool)).all()),
        "forecast_metric_values_present": forecast_metric_values_present,
        "routing_metric_values_present": routing_metric_values_present,
        "all_required_metric_values_present": bool(forecast_metric_values_present and routing_metric_values_present),
        "routing_nmi_meets_minimum": bool(not routing_nmi_values.empty and routing_nmi_values.mean() >= min_nmi),
        "routing_ari_meets_minimum": bool(not routing_ari_values.empty and routing_ari_values.mean() >= min_ari),
        "no_wtb_or_sdwpf_source": all(
            "sdwpf" not in str(row.get("source_files", "")).lower()
            and "wtbdata" not in str(row.get("source_files", "")).lower()
            and "kdd" not in str(row.get("source_files", "")).lower()
            for row in cache_rows
        ),
    }
    data_and_protocol_complete = bool(
        checks["all_cache_dirs_exist"]
        and checks["cache_dataset_is_external_wind"]
        and checks["cache_license_is_cc_by_4"]
        and checks["required_farms_cached"]
        and checks["all_expected_runs_complete"]
        and checks["cross_farm_both_directions_complete"]
        and checks["chronological_sanity_complete"]
        and checks["all_required_metric_files_exist"]
        and checks["all_required_metric_values_present"]
        and checks["no_wtb_or_sdwpf_source"]
    )
    portable_ready = bool(
        data_and_protocol_complete
        and checks["routing_nmi_meets_minimum"]
        and checks["routing_ari_meets_minimum"]
    )
    if portable_ready:
        status = "portable_mechanism_ready"
        claim_gate = "portable_mechanism_passed"
    elif data_and_protocol_complete:
        status = "complete_but_within_wtb_only"
        claim_gate = "within_wtb_only"
    else:
        status = "blocked_external_wind_incomplete"
        claim_gate = "blocked_not_citable"
    report = {
        "status": status,
        "claim_gate": claim_gate,
        "checks": checks,
        "expected_runs": expected_runs,
        "complete_runs": complete_runs,
        "seeds": seed_list,
        "required_models": _parse_csv_strings(required_models),
        "routing_required_models": sorted(routing_model_set),
        "expected_routing_runs": expected_routing_runs,
        "complete_routing_runs": int(routing_df["complete"].sum()) if not routing_df.empty and "complete" in routing_df else 0,
        "mean_nmi": float(routing_nmi_values.mean()) if not routing_nmi_values.empty else None,
        "mean_ari": float(routing_ari_values.mean()) if not routing_ari_values.empty else None,
        "mean_overall_rmse": float(overall_values.mean()) if not overall_values.empty else None,
        "mean_switch_rmse": float(switch_values.mean()) if not switch_values.empty else None,
        "mean_boundary_rmse": float(boundary_values.mean()) if not boundary_values.empty else None,
        "mean_gate_entropy": float(routing_entropy_values.mean()) if not routing_entropy_values.empty else None,
        "min_nmi": float(min_nmi),
        "min_ari": float(min_ari),
        "required_cross_farm_pairs": sorted([f"{src}->{dst}" for src, dst in required_lofo_pairs]),
        "license": EXTERNAL_LICENSE,
        "source_urls": EXTERNAL_SOURCE_URLS,
        "static_notes": EXTERNAL_STATIC_NOTES,
    }
    save_json(output_dir / "external_wind_guard.json", report)
    return output_dir


def _expert_usage_present(value: Any) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return False
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, list) or len(parsed) == 0:
        return False
    numeric = pd.to_numeric(pd.Series(parsed), errors="coerce").dropna()
    return bool(len(numeric) > 0)


def _cache_status(cache_dir: Path) -> dict[str, Any]:
    required = [
        "metadata.json",
        "features.npy",
        "physics.npy",
        "regime_primary.npy",
        "regime_primary_valid.npy",
        "regime_valid.npy",
        "anchor_index.npy",
        "node_ids.npy",
    ]
    metadata_path = cache_dir / "metadata.json"
    metadata = {}
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as handle:
            metadata = json.load(handle)
    source_files = metadata.get("source_url", "")
    farm = str(metadata.get("farm", ""))
    split = str(metadata.get("external_split", ""))
    target_farm = str(metadata.get("target_farm", ""))
    fingerprint = metadata.get("external_source_fingerprint", {})
    source_fingerprint_present = bool(isinstance(fingerprint, dict) and fingerprint.get("signature"))
    metadata_complete = (
        _external_cache_metadata_complete(metadata_path, farm=farm, split=split, target_farm=target_farm)
        and source_fingerprint_present
    )
    return {
        "cache_dir": str(cache_dir),
        "complete": all((cache_dir / name).exists() for name in required) and metadata_complete,
        "files_complete": all((cache_dir / name).exists() for name in required),
        "metadata_schema_complete": metadata_complete,
        "dataset": metadata.get("dataset", ""),
        "farm": farm,
        "target_farm": target_farm,
        "split_id": split,
        "license": metadata.get("license", ""),
        "split_farm_roles": json.dumps(metadata.get("split_farm_roles", {}), sort_keys=True),
        "source_files": metadata.get("source_files", source_files),
        "source_fingerprint_present": source_fingerprint_present,
        "source_fingerprint_signature": fingerprint.get("signature", "") if isinstance(fingerprint, dict) else "",
        "source_fingerprint_files": fingerprint.get("n_files", "") if isinstance(fingerprint, dict) else "",
        "source_fingerprint_scada_files": fingerprint.get("n_scada_files", "") if isinstance(fingerprint, dict) else "",
        "source_fingerprint_scada_zip_members": fingerprint.get("n_scada_zip_members", "") if isinstance(fingerprint, dict) else "",
        "num_nodes": metadata.get("num_nodes"),
        "num_steps": metadata.get("num_steps"),
    }


def _external_run_status(suite_dir: Path, seeds: list[int], required_models: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summaries = sorted(suite_dir.rglob("training_summary.json")) if suite_dir.exists() else []
    found: list[dict[str, Any]] = []
    for summary_path in summaries:
        run_dir = summary_path.parent
        with summary_path.open("r", encoding="utf-8") as handle:
            summary = json.load(handle)
        metrics_path = run_dir / "test_metrics" / "metrics.json"
        metrics = {}
        if metrics_path.exists():
            with metrics_path.open("r", encoding="utf-8") as handle:
                metrics = json.load(handle)
        gate_alignment = metrics.get("gate_alignment", {}) if isinstance(metrics, dict) else {}
        expert_usage = gate_alignment.get("expert_usage") if isinstance(gate_alignment, dict) else None
        metrics_dir = run_dir / "test_metrics"
        found.append(
            {
                "run_dir": str(run_dir),
                "model": summary.get("label", summary.get("model_mode", "")),
                "seed": int(summary.get("seed", -1)),
                "dataset": summary.get("dataset", "external_wind"),
                "farm": summary.get("farm") or _infer_external_farm_from_path(run_dir),
                "target_farm": summary.get("target_farm") or _infer_external_target_farm_from_path(run_dir),
                "split_id": summary.get("external_split") or _infer_external_split_from_path(run_dir),
                "complete": metrics_path.exists(),
                "metric_files_complete": _metrics_dir_complete(metrics_dir),
                "overall_rmse": metrics.get("overall", {}).get("rmse"),
                "switch_rmse": metrics.get("switch_window", {}).get("rmse"),
                "boundary_rmse": _external_boundary_rmse(metrics_dir),
                "nmi": gate_alignment.get("nmi") if isinstance(gate_alignment, dict) else None,
                "ari": gate_alignment.get("ari") if isinstance(gate_alignment, dict) else None,
                "expert_usage_entropy": gate_alignment.get("expert_usage_entropy") if isinstance(gate_alignment, dict) else None,
                "expert_usage": json.dumps(expert_usage) if expert_usage is not None else "",
            }
        )
    for model in required_models:
        for seed in seeds:
            for split_id, farm, target in [
                ("leave-one-farm-out", "kelmarsh", "penmanshiel"),
                ("leave-one-farm-out", "penmanshiel", "kelmarsh"),
                ("chronological", "kelmarsh", ""),
                ("chronological", "penmanshiel", ""),
            ]:
                candidates = [
                    row
                    for row in found
                    if str(row["model"]) == model
                    and int(row["seed"]) == int(seed)
                    and str(row.get("split_id", "")) == split_id
                    and str(row.get("farm", "")) == farm
                    and (split_id == "chronological" or str(row.get("target_farm", "")) == target)
                ]
                if candidates:
                    rows.append(candidates[0])
                else:
                    rows.append(
                        {
                            "model": model,
                            "seed": seed,
                            "farm": farm,
                            "target_farm": target,
                            "split_id": split_id,
                            "run_dir": "",
                            "complete": False,
                            "metric_files_complete": False,
                        }
                    )
    return rows


def _external_boundary_rmse(metrics_dir: Path, rated_wind: float = 10.5, boundary_band: float = 1.0) -> float | None:
    required = [
        "pred.npy",
        "target.npy",
        "mask.npy",
        "regime_primary.npy",
        "regime_primary_valid.npy",
        "anchor_physics.npy",
    ]
    if not all((metrics_dir / name).exists() for name in required):
        return None
    try:
        pred = np.load(metrics_dir / "pred.npy")
        target = np.load(metrics_dir / "target.npy")
        mask = np.load(metrics_dir / "mask.npy")
        regime = np.load(metrics_dir / "regime_primary.npy")
        valid = np.load(metrics_dir / "regime_primary_valid.npy")
        physics = np.load(metrics_dir / "anchor_physics.npy")
    except (OSError, ValueError):
        return None
    if pred.shape != target.shape:
        return None
    mask_arr = np.asarray(mask, dtype=np.float32)
    if mask_arr.ndim == 2 and pred.ndim == 3:
        mask_arr = mask_arr[:, None, :]
    if mask_arr.shape != pred.shape:
        try:
            mask_arr = np.broadcast_to(mask_arr, pred.shape).astype(np.float32)
        except ValueError:
            return None
    wspd = np.asarray(physics)[..., 0] if np.asarray(physics).ndim >= 3 else np.asarray(physics)
    regime_arr = np.asarray(regime)
    valid_arr = np.asarray(valid)
    try:
        boundary = (
            np.isin(regime_arr, [1, 2])
            & (valid_arr > 0)
            & (np.abs(np.asarray(wspd, dtype=np.float32) - float(rated_wind)) <= float(boundary_band))
        )
    except ValueError:
        return None
    if boundary.ndim == 2 and pred.ndim == 3:
        boundary = boundary[:, None, :]
    try:
        selector = np.broadcast_to(boundary, pred.shape)
    except ValueError:
        return None
    weight = mask_arr * selector.astype(np.float32)
    denom = float(weight.sum())
    if denom <= 0.0:
        return None
    mse = float((((np.asarray(pred) - np.asarray(target)) ** 2) * weight).sum() / denom)
    return float(math.sqrt(max(mse, 0.0)))


def _metrics_dir_complete(metrics_dir: Path) -> bool:
    required = [
        "metrics.json",
        "pred.npy",
        "target.npy",
        "mask.npy",
        "regime_primary.npy",
        "regime_primary_valid.npy",
        "anchor_index.npy",
        "anchor_physics.npy",
    ]
    return all((metrics_dir / name).exists() for name in required)


def _infer_external_split_from_path(path: Path) -> str:
    text = str(path).lower().replace("\\", "/")
    if "leave_one_farm_out" in text or "leave-one-farm-out" in text or "_to_" in text:
        return "leave-one-farm-out"
    if "chronological" in text:
        return "chronological"
    return ""


def _infer_external_farm_from_path(path: Path) -> str:
    text = str(path).lower().replace("\\", "/")
    if "penmanshiel_to_kelmarsh" in text:
        return "penmanshiel"
    if "kelmarsh_to_penmanshiel" in text:
        return "kelmarsh"
    if "penmanshiel" in text:
        return "penmanshiel"
    if "kelmarsh" in text:
        return "kelmarsh"
    return ""


def _infer_external_target_farm_from_path(path: Path) -> str:
    text = str(path).lower().replace("\\", "/")
    if "penmanshiel_to_kelmarsh" in text:
        return "kelmarsh"
    if "kelmarsh_to_penmanshiel" in text:
        return "penmanshiel"
    if _infer_external_split_from_path(path) == "leave-one-farm-out":
        farm = _infer_external_farm_from_path(path)
        if farm == "kelmarsh":
            return "penmanshiel"
        if farm == "penmanshiel":
            return "kelmarsh"
    return ""


def _parse_csv_strings(values: Iterable[str] | str) -> list[str]:
    if isinstance(values, str):
        return [token.strip() for token in values.split(",") if token.strip()]
    return [str(token).strip() for token in values if str(token).strip()]


def _parse_csv_ints(values: Iterable[int] | str) -> list[int]:
    if isinstance(values, str):
        return [int(token.strip()) for token in values.split(",") if token.strip()]
    return [int(value) for value in values]


def sha256_file(path: Path, max_mb: float | None = None) -> str:
    limit = None if max_mb is None else int(float(max_mb) * 1024 * 1024)
    digest = hashlib.sha256()
    read = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            if limit is not None and read + len(chunk) > limit:
                digest.update(chunk[: max(0, limit - read)])
                break
            digest.update(chunk)
            read += len(chunk)
    return digest.hexdigest()
