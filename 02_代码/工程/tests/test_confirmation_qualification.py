import importlib.util
import io
import zipfile
from repo_paths import Path, repository_root
import numpy as np
import pandas as pd
import pytest

path = Path(repository_root()) / "experiments/independent_confirmation_20261019/qualify_hill_of_towie.py"
spec = importlib.util.spec_from_file_location("confirmation_schema_test", path)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def test_sealed_year_refused_before_any_zip_access(tmp_path):
    with pytest.raises(ValueError, match="sealed 2025"):
        m.audit_year(tmp_path / "2025.zip", 2025, tmp_path)


def test_required_fields_and_join_key_are_bound():
    columns = ["TimeStamp", "StationId", *m.TABLES["tblSCTurGrid"]]
    result = m.inspect_header((",".join(columns) + "\n").encode(), "tblSCTurGrid")
    assert result["station"] == "StationId"
    assert m.read_header(io.BytesIO((",".join(columns) + "\n").encode("utf-16")), "tblSCTurGrid")["encoding"] == "utf-16"
    with pytest.raises(ValueError, match="Required field"):
        m.inspect_header(b"TimeStamp,StationId,wtc_ActPower_mean\n", "tblSCTurGrid")


def test_exact_utc_coordinates_no_flooring_or_unknown_station():
    frame = pd.DataFrame(dict(TimeStamp=["2024-01-01 00:00:00", "2024-01-01 00:10:00"], StationId=[2304510, 2304530]))
    indices, ids = m.coordinates(frame, 2024, "StationId")
    np.testing.assert_array_equal(indices, [0, 41])
    boundary = pd.DataFrame(dict(TimeStamp=["2025-01-01 00:00:00"], StationId=[2304510]))
    end_index, _ = m.coordinates(boundary, 2024, "StationId")
    assert end_index[0] == 366 * 144 * 21
    frame.loc[0, "TimeStamp"] = "2024-01-01 00:00:01"
    with pytest.raises(ValueError, match="off the UTC"):
        m.coordinates(frame, 2024, "StationId")
    frame.loc[0, "TimeStamp"] = "2024-01-01 00:00:00"
    frame.loc[0, "StationId"] = 1
    with pytest.raises(ValueError, match="station ID"):
        m.coordinates(frame, 2024, "StationId")


def test_synthetic_monthly_source_audit_preserves_negative_power(tmp_path):
    archive = tmp_path / "synthetic_2023.zip"
    with zipfile.ZipFile(archive, "w") as z:
        for table, fields in m.TABLES.items():
            for month in range(1, 13):
                values = {"TimeStamp": [f"2023-{month:02d}-01 00:00:00"] * 21,
                          "StationId": np.arange(2304510, 2304531)}
                for field in fields:
                    values[field] = np.arange(21, dtype=float)
                if table == "tblSCTurGrid":
                    values["wtc_ActPower_mean"][0] = -1
                z.writestr(f"{table}_2023_{month:02d}.csv", pd.DataFrame(values).to_csv(index=False))
    result = m.audit_year(archive, 2023, tmp_path)
    assert result["tables"]["tblSCTurGrid"]["negative_observed_preserved"]["wtc_ActPower_mean"] == 12
    assert result["tables"]["tblSCTurbine"]["unique_cells"] == 252


def test_one_shot_dependency_waits_only_historical_receipts(tmp_path):
    p = Path(repository_root()) / "experiments/independent_confirmation_20261019/launch_qualification_when_acquired.py"
    s = importlib.util.spec_from_file_location("qualification_dependency_test", p)
    dependency = importlib.util.module_from_spec(s)
    s.loader.exec_module(dependency)
    assert dependency.ready(tmp_path) is False
    for year in (2023, 2024):
        (tmp_path / f"receipt_{year}.json").write_text("{}", encoding="utf-8")
    assert dependency.ready(tmp_path) is True
    (tmp_path / "failure_2024.json").write_text("{}", encoding="utf-8")
    with pytest.raises(RuntimeError, match="acquisition failed"):
        dependency.ready(tmp_path)
