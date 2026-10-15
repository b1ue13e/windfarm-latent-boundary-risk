"""Rebuild declared external windows from raw SCADA before normalization.

Window offsets are frozen historical choices, not reselected by replay performance.
The legacy window script sliced standardized arrays and rewrote scaler metadata;
this corrected version is distinct and must not be advertised as bitwise legacy replay.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from windfarm_moe.external_wind import (ExternalWindConfig, _read_external_scada,
    _read_external_coords, _write_cache_from_frame, _find_first_file, _find_column)
from replay_provenance import provenance, finalize, write_json

FARMS={'kelmarsh':(120,6),'penmanshiel':(720,14),'la_haute_borne':(0,4)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--farm',choices=list(FARMS),required=True)
    p.add_argument('--output-root',type=Path,default=ROOT/'artifacts/raw_replay_external_20261015')
    a=p.parse_args(); offset,n_nodes=FARMS[a.farm]
    out=a.output_root.resolve()/a.farm
    if not out.is_relative_to(ROOT/'artifacts'):
        raise ValueError('Output must be under repository artifacts')
    if out.exists():raise FileExistsError(f'Refusing to overwrite {out}')
    source=ROOT/'data/external_wind'/a.farm
    inputs=sorted(x for x in source.iterdir() if x.is_file() and x.suffix.lower() in ('.csv','.zip'))
    if not inputs:raise FileNotFoundError(source)
    provenance(out,inputs,{'farm':a.farm,'offset_days':offset,'window_days':245,
        'train_days':180,'val_days':30,'test_days':35,'rated_wind':10.5,'pitch_threshold':2.,
        'normalization':'fit on selected-window training observations only',
        'legacy_equivalence':'not asserted; raw-window restandardization correction'})
    raw=_read_external_scada(source)
    node_ids=sorted(raw['node_id'].astype(str).unique().tolist())
    if len(node_ids)!=n_nodes:raise ValueError(f'Frozen node population changed: {node_ids}')
    coords=_read_external_coords(source,node_ids)
    static_path=_find_first_file(source,['*turbine*static*.csv','*static*.csv','*location*.csv','*coordinate*.csv','*metadata*.csv'])
    if static_path is None:
        raise ValueError('Missing coordinate source; regular synthetic layout is forbidden')
    static=pd.read_csv(static_path)
    for aliases in [['turbine_id','Alternative Title','Turbine','TurbineName','Identity','id'],
                    ['x','easting','longitude','lon'],['y','northing','latitude','lat']]:
        if _find_column(static.columns,aliases,required=False) is None:
            raise ValueError(f'Missing coordinate field in {static_path}: {aliases}')
    if not set(node_ids).issubset(set(coords.node_id.astype(str))) or not np.isfinite(coords[['x','y']].to_numpy()).all():
        raise ValueError('Missing actual coordinates; synthetic topology fallback forbidden')
    begin=raw['timestamp'].min()+pd.Timedelta(days=offset)
    end=begin+pd.Timedelta(days=245)
    window=raw[(raw['timestamp']>=begin)&(raw['timestamp']<end)].copy()
    if window.empty:raise ValueError('Frozen window not covered by source')
    # Reindex boundary timestamps as missing grid cells if no raw sample is present.
    # No value is invented; _write_cache_from_frame constructs masks for these NaNs.
    for t in (begin,end-pd.Timedelta(minutes=10)):
        if not (window['timestamp']==t).any():
            pad={c:np.nan for c in window.columns};pad.update(timestamp=t,node_id=node_ids[0])
            window=pd.concat([window,pd.DataFrame([pad])],ignore_index=True)
    config=ExternalWindConfig(root_dir=ROOT,farm=a.farm,source_dir=ROOT/'data/external_wind')
    cache=out/'cache'
    _write_cache_from_frame(window,coords,config,cache,
        split_bounds_override={'train':[0,25920],'val':[25920,30240],'test':[30240,35280]},
        source_files=raw.attrs.get('source_file',''))
    meta=json.loads((cache/'metadata.json').read_text(encoding='utf-8'))
    if meta['num_steps']!=35280 or meta['num_nodes']!=n_nodes:
        raise ValueError('Rebuilt external shape does not match frozen window')
    meta.update(window_offset_days=offset,window_begin=str(begin),window_end_exclusive=str(end),
                replay_protocol='raw-window-before-standardization-v2')
    write_json(cache/'metadata.json',meta)
    finalize(out)
    print('RAW_EXTERNAL_CACHE_EXECUTED',a.farm,meta['num_steps'],meta['num_nodes'],flush=True)


if __name__=='__main__':main()
