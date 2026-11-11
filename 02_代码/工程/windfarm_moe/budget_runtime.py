"""Frozen-draw orchestration; no RNG, model import, training or scheduler."""
from dataclasses import asdict, dataclass
from fractions import Fraction as F
import numpy as np

from .budget_diagnostic_core import COORDINATES, SEEDS, map_pair, score_pair, combine_fits, _digest
from .budget_intervals import infer_family, metric_record
from .budget_sources import QualifiedSource, array_sha256, file_sha256


@dataclass(frozen=True)
class DiagnosticRun:
    rows: tuple
    metadata: dict
    trace: dict


class ResourceAdmissionError(RuntimeError):
    """Technical stop before scoring; never a scientific negative result."""
    def __init__(self, plan):
        self.plan=plan
        super().__init__('Exact grouped work exceeds the declared execution budget; no scores computed')


def execution_plan(source):
    counts={(1,)*source.spec.n_days}
    for row in source.indices:counts.add(tuple(map(int,np.bincount(row,minlength=source.spec.n_days))))
    cells=sum(len(table) for table,_ in source.groups.values())
    return dict(unique_day_configurations=len(counts),grouped_rows_over_fits=cells,
        exact_group_visits_upper=len(counts)*4*cells,
        original_n_scored=source.spec.n_scored,
        rule='Upper work before memo reuse: configs times four settings times all fit-group rows',
        selection_uses_outcomes=False)


def _mapping_receipt(mapping):
    return dict(status=mapping.status,method=mapping.method,A=mapping.base_budget,B=mapping.budget,
        Nw=mapping.n_weight,coefficient=mapping.coefficient,ideal_coefficient=mapping.ideal_coefficient,
        residual=mapping.residual,action_error=mapping.action_error,
        action_error_kind=getattr(mapping,'action_error_kind','EXACT_L1'),branch=mapping.branch,
        active_weight=None if mapping.actions is None else int(np.asarray(mapping.weights)[np.asarray(mapping.actions)>0].sum()),
        coefficient_neighbors=len(mapping.neighbors))


def evaluate_frozen_source(source: QualifiedSource, *, allow_archived=False, progress=None,
                           max_exact_group_visits=10_000_000,backend='scalar'):
    """Evaluate all five fits and all nominal draws, without qualification filters.

    Identical whole day-weight configurations may reuse *all* deterministic work.
    Every original draw ID still has an explicit configuration mapping and enters
    the interval calculation. Compression never merges approximately equal rows.
    """
    if source.mode=='ARCHIVED' and not allow_archived:
        raise PermissionError('Real action evaluation is not enabled by default')
    if backend not in ('scalar','vector_exact'):raise ValueError('Unknown verified backend')
    prepared={};vector_sha=None
    if backend=='vector_exact':
        from . import budget_vector_exact as vector
        vector_sha=file_sha256(vector.__file__)
        prepared={s:(vector.PreparedActions.make(t[:,1]),vector.PreparedActions.make(t[:,2])) for s,(t,c) in source.groups.items()}
    plan=execution_plan(source)
    if max_exact_group_visits is None or max_exact_group_visits<=0:
        raise ValueError('Declare a finite positive computational work budget')
    if plan['exact_group_visits_upper']>max_exact_group_visits:
        raise ResourceAdmissionError(dict(plan,declared_work_budget=max_exact_group_visits))
    n_days=source.spec.n_days
    cache={};configurations={};draw_to_config=[]
    computation_cache={}

    def evaluate_counts(day_counts):
        key=tuple(map(int,day_counts))
        if key in cache:return cache[key]
        outputs={};receipts={}
        seed_weights={seed:np.asarray(counts,dtype=np.int64)*np.asarray(key,dtype=np.int64)[table[:,0].astype(np.int64)]
                      for seed,(table,counts) in source.groups.items()}
        weight_digests={seed:array_sha256(w) for seed,w in seed_weights.items()}
        for anchor in ('P','Z'):
            for method in ('M','S'):
                setting_id='A'+anchor+'_'+method
                scores={};fits={}
                for seed in SEEDS:
                    table,multiplicity=source.groups[seed]
                    weights=seed_weights[seed]
                    table_key=source.identity['source_records'][seed]['group_table']
                    weights_digest=weight_digests[seed]
                    memo=(table_key,weights_digest,anchor,method)
                    if memo not in computation_cache:
                        if backend=='vector_exact':
                            setting=vector.map_pair_fast(table[:,1],table[:,2],anchor,method,weights,prepared=prepared[seed])
                            score=vector.score_pair_fast(table[:,3],setting.P,setting.Z)
                        else:
                            setting=map_pair(table[:,1],table[:,2],anchor,method,weights)
                            score=score_pair(table[:,3],setting.P,setting.Z)
                        pair_residual=None if setting.P.residual is None or setting.Z.residual is None else setting.Z.residual-setting.P.residual
                        receipt=dict(P=_mapping_receipt(setting.P),Z=_mapping_receipt(setting.Z),
                            pair_residual=pair_residual,score=asdict(score),weights_sha256=weights_digest,group_table_sha256=table_key)
                        computation_cache[memo]=(score,receipt)
                    score,receipt=computation_cache[memo]
                    scores[seed]=score;fits[seed]=receipt
                combined=combine_fits(scores)
                receipts[setting_id]=dict(fits=fits,combined=asdict(combined))
                for metric in ('U','V'):outputs[setting_id+'_'+metric]=metric_record(combined,metric)
        cache[key]=outputs
        config_id=len(configurations)
        configurations[key]=dict(config_id=config_id,day_counts=key,settings=receipts)
        if progress:progress(dict(unique_day_configs=len(cache),last_day_counts=key))
        return outputs

    points=evaluate_counts(np.ones(n_days,dtype=np.int64))
    draws={k:[] for k in COORDINATES}
    for idx in source.indices:
        weights=np.bincount(idx,minlength=n_days)
        records=evaluate_counts(weights)
        draw_to_config.append(configurations[tuple(map(int,weights))]['config_id'])
        for key in COORDINATES:draws[key].append(records[key])
    trace=dict(configurations=list(configurations.values()),draw_to_config=draw_to_config,
        point_config=configurations[(1,)*n_days]['config_id'],draw_indices_sha256=array_sha256(source.indices),
        day_ids=list(range(source.spec.first_day,source.spec.first_day+n_days)),
        grouping='EXACT_BITWISE_DAY_P_Z_S_NO_QUANTIZATION',all_nominal_draws_retained=True,
        numeric_thresholds_changed=False)
    identity=dict(source.identity,mapping_receipts_sha256=_digest(trace),runtime_sha256=file_sha256(__file__),
                  mapping_backend=backend,vector_backend_sha256=vector_sha)
    rows,metadata=infer_family(points,draws,span=identity['span'],source_identity=identity)
    metadata.update(unique_day_configurations=len(cache),unique_mapping_computations=len(computation_cache),
        full_n_scored=source.spec.n_scored,exact_group_counts={s:len(v[0]) for s,v in source.groups.items()},
        mode=source.mode,execution_plan=plan,declared_work_budget=max_exact_group_visits)
    return DiagnosticRun(rows,metadata,trace)
