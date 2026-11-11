"""Read-only frozen-source qualification and exact-equivalent row compression."""
from dataclasses import dataclass
import hashlib
import json
from repo_paths import Path, repository_root
import numpy as np

from .budget_diagnostic_core import SEEDS, N_BOOT, _digest


def file_sha256(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def array_sha256(value):
    a=np.ascontiguousarray(value)
    digest=hashlib.sha256(json.dumps((a.dtype.str,a.shape)).encode())
    digest.update(memoryview(a).cast('B'))
    return digest.hexdigest()


@dataclass(frozen=True)
class PopulationSpec:
    anchor_start: int
    anchor_stop: int
    n_nodes: int
    n_scored: int
    first_day: int
    n_days: int


ARCHIVED_SPEC=PopulationSpec(30240,35273,134,672939,210,35)
FROZEN_RULES_SHA256='934fc72e93bbe122e2efed21dfe8691212187885f72dd91bdbdea8fc3a232e57'
FROZEN_BINDINGS_SHA256='b4462bf433b836bc358a702d7adf3c3f99279df41b46f68ea5ff0b729e6164af'


@dataclass(frozen=True)
class QualifiedSource:
    mode: str
    spec: PopulationSpec
    groups: dict
    # Per seed: unique (day,P,Z,S) rows and exact original multiplicities.
    identity: dict
    indices: np.ndarray


def qualify_arrays(runs,indices,*,spec,mode,rules_sha256,span,receipt=None):
    if mode not in ('SYNTHETIC','ARCHIVED') or span not in (1,3,7):raise ValueError('Unknown mode/span')
    if set(runs)!=set(SEEDS):raise ValueError('All five fixed fits are required')
    if mode=='ARCHIVED' and (spec!=ARCHIVED_SPEC or not receipt or receipt.get('verified_bytes') is not True):
        raise ValueError('Original frozen population and verified archive receipts required')
    if len(rules_sha256)!=64:raise ValueError('Missing frozen rule hash')
    idx=np.array(indices,copy=True)
    if idx.dtype.kind not in 'iu' or idx.shape!=(N_BOOT,spec.n_days) or np.any(idx<0) or np.any(idx>=spec.n_days):
        raise ValueError('Original draw shape/day identities required')
    idx.flags.writeable=False
    expected_anchors=np.arange(spec.anchor_start,spec.anchor_stop,dtype=np.int64)
    shape=(len(expected_anchors),spec.n_nodes)
    groups={};fingerprints={};common=None
    for seed in SEEDS:
        run=runs[seed]
        a,m,s=np.asarray(run['anchors']),np.asarray(run['mask']),np.asarray(run['S'])
        p,z=np.asarray(run['P'],dtype=np.float64),np.asarray(run['Z'],dtype=np.float64)
        if a.dtype.kind not in 'iu' or not np.array_equal(a,expected_anchors):raise ValueError('Frozen anchor mismatch')
        if m.dtype!=bool or m.shape!=shape or s.shape!=shape or p.shape!=shape or z.shape!=shape:
            raise ValueError('Source grid/mask mismatch')
        if int(m.sum())!=spec.n_scored:raise ValueError('Frozen scored population mismatch')
        nodes=tuple(run.get('node_ids',()))
        if len(nodes)!=spec.n_nodes or len(set(nodes))!=len(nodes):raise ValueError('Node axis identity required')
        population=(array_sha256(a),array_sha256(m),nodes)
        if common is not None and population!=common:raise ValueError('Cross-fit population/order mismatch')
        common=population
        values=np.column_stack((p[m],z[m],np.asarray(s[m],dtype=np.float64)))
        if not np.isfinite(values).all() or np.any(values<0):raise ValueError('Nonfinite/negative scored action or target')
        days=np.broadcast_to((a//144)[:,None],shape)[m]
        if not np.array_equal(np.unique(days),np.arange(spec.first_day,spec.first_day+spec.n_days)):
            raise ValueError('Original day identities missing or compressed')
        # Exact equality only: no bins, quantization, row/outcome filters or rounding.
        table=np.column_stack((days-spec.first_day,values))
        # Bit identities also preserve signed zero in positive-budget identities.
        unique_bits,counts=np.unique(table.view(np.uint64),axis=0,return_counts=True)
        unique=unique_bits.view(np.float64)
        unique.flags.writeable=False;counts.flags.writeable=False
        groups[seed]=(unique,counts)
        fingerprints[seed]=dict(P=array_sha256(p[m]),Z=array_sha256(z[m]),S=array_sha256(s[m]),
            anchors=population[0],mask=population[1],node_ids=nodes,group_table=array_sha256(unique),
            group_counts=array_sha256(counts))
    source_hash=_digest(dict(mode=mode,spec=spec.__dict__,runs=fingerprints,receipt=receipt))
    identity=dict(mode=mode,verified=True,source_sha256=source_hash,rules_sha256=rules_sha256,
                  draw_sha256=array_sha256(idx),span=span,source_records=fingerprints,
                  n_scored=spec.n_scored,n_days=spec.n_days,receipt=receipt,
                  source_validator_sha256=file_sha256(__file__))
    return QualifiedSource(mode,spec,groups,identity,idx)


def verify_bound_archives(bindings_path,rules_path,run_directories,*,span,trace_path=None):
    """Library-only read/qualification. Does not evaluate or map real actions.

    Never substitutes a changed population or a local 'best available' file.
    Current repair tests call the synthetic array adapter, not this real loader.
    """
    bindings_path,rules_path=Path(bindings_path),Path(rules_path)
    if file_sha256(bindings_path)!=FROZEN_BINDINGS_SHA256 or file_sha256(rules_path)!=FROZEN_RULES_SHA256:
        raise ValueError('Frozen V2 rules/source-binding bytes changed')
    bindings=json.loads(bindings_path.read_text(encoding='utf-8'))
    rules=json.loads(rules_path.read_text(encoding='utf-8'))
    if tuple(rules['family']['coordinate_order'])!=('AP_M_U','AP_M_V','AP_S_U','AP_S_V','AZ_M_U','AZ_M_V','AZ_S_U','AZ_S_V'):
        raise ValueError('Frozen family changed')
    if rules['inference']['n_boot']!=N_BOOT or tuple(rules['pair']['seeds'])!=SEEDS:
        raise ValueError('Frozen draws/fits changed')
    if rules['population']['anchors_half_open']!=[30240,35273] or rules['population']['expected_scored_N']!=672939:
        raise ValueError('Frozen population changed')
    if set(run_directories)!=set(SEEDS):raise ValueError('Missing fixed run directory')
    receipt=dict(verified_bytes=True,bindings_sha256=file_sha256(bindings_path),rules_sha256=file_sha256(rules_path),members={})
    # Verify every expected local manifest and consumed protocol before reading arrays.
    for entry in bindings['source_references'].values():
        if file_sha256(entry['path'])!=entry['sha256']:raise ValueError('Frozen source document mismatch')
    for run in bindings['runs']:
        if file_sha256(run['local_manifest'])!=run['local_manifest_sha256']:raise ValueError('Original manifest mismatch')
        seed=run['seed'];directory=Path(run_directories[seed])
        for name in ('actions.npz','coordinates.npz'):
            expected=run['members'][name];path=directory/name
            if path.stat().st_size!=expected['bytes'] or file_sha256(path)!=expected['sha256']:
                raise ValueError('Archive byte identity mismatch: '+str(seed)+'/'+name)
            receipt['members'][str(seed)+'/'+name]=expected['sha256']
    entry=next(x for x in bindings['draw_traces'] if x['span']==span)
    path=Path(trace_path or entry['local_path'])
    if file_sha256(path)!=entry['file_sha256']:raise ValueError('Original draw archive mismatch')
    with np.load(path,allow_pickle=False) as archive:idx=archive[entry['indices_key']].copy()
    if list(idx.shape)!=entry['index_shape'] or hashlib.sha256(idx.tobytes()).hexdigest()!=entry['original_draw_sha256']:
        raise ValueError('Original index order/hash mismatch')
    receipt['draw_archive_sha256']=entry['file_sha256']
    runs={}
    for run in bindings['runs']:
        directory=Path(run_directories[run['seed']])
        with np.load(directory/'actions.npz',allow_pickle=False) as actions, np.load(directory/'coordinates.npz',allow_pickle=False) as coordinates:
            runs[run['seed']]=dict(P=actions[run['P_action_key']].copy(),Z=actions[run['Z_action_key']].copy(),
                anchors=coordinates['evaluate__anchors'].copy(),mask=coordinates['evaluate__mask'].copy(),
                S=coordinates['evaluate__shortfall'].copy(),node_ids=tuple(range(134)))
            # Positional node identity is justified by the identical verified original coordinate bytes.
    return qualify_arrays(runs,idx,spec=ARCHIVED_SPEC,mode='ARCHIVED',rules_sha256=receipt['rules_sha256'],span=span,receipt=receipt)
