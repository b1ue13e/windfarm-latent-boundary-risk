"""Assemble literature audit records; no experiment or measurement data are read."""
from pathlib import Path
import csv, hashlib, json

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent

def meta(name):
    p=ROOT/(name+'_crossref.json')
    if not p.exists(): p=ROOT/(name+'_crossref_previous_verified.json')
    o=json.loads(p.read_text(encoding='utf-8-sig'))
    return o.get('message',o),str(p.relative_to(OUT))

def dates(m,key):
    part=m.get(key,{}).get('date-parts',[[]])[0]
    return '-'.join(str(x).zfill(4 if i==0 else 2) for i,x in enumerate(part)) or 'UNKNOWN'

DETAILS = [
dict(key='mlwa',id='L01',role='mainstream',version='Publisher PDF provided by user; 15 pages; exact identity verified',online='2026-07-21 (PDF front matter)',read_scope='Prior complete 15-page reading record; this round selectively rechecked pp6-9 and13; Tables2/5/6; not code/data/SI replication',
 source_url='https://www.sciencedirect.com/science/article/pii/S2666827026001222',original='E:/论文3/1-s2.0-S2666827026001222-main.pdf',
 knowledge='Operation-based residual hybrid plus Gaussian/QR UQ and local perturbation connect uncertainty to turbine control regimes; deterministic and probabilistic baselines present',
 power_history='No P predictor among seven SCADA inputs; previous single minute predicts next minute P (§2.2/2.4)',state='Measured blade angle and other SCADA; operation-based cp; not recovered score after strong P history',fresh_p='No matched fresh-P substitution in supplied article',endpoints='rRMSE/R2; nCRPS; pinball; bilateral90%PICP; reserve illustration in discussion',
 difference='Fixed common commitment plus strong consequence history; separate measured pitch/recovered score; matched fresh-P alternatives; paired C/R/U/V',
 missing='Code/private data/external SI not obtained; local perturbation is not conditional information necessity',forbidden='No first state-related UQ; no assertion that article lacks probabilistic/deep baselines; no pitch redundancy inference'),
dict(key='seta',id='L02',role='mainstream',version='Published article identity; publisher preview only; final full text NOT obtained',online='UNKNOWN; DOI created2026-09-27 is not online date',read_scope='Publisher abstract/introduction/contribution and section previews; root and prior source notes; not whole methods/results',
 source_url='https://www.sciencedirect.com/science/article/pii/S2213138826006247',original='research_audit/reserve_allocation_paper_diligence_20261020/NEIGHBOR_REVIEW.md (reading log only)',
 knowledge='Regime/horizon quantile and conformal calibration; rare-regime shrinkage; lower-bound shortfall proxy explicitly distinguished from direct operating cost',
 power_history='UNKNOWN complete input list',state='Regime-conditioned quantiles; complete pitch/measurement construction UNKNOWN',fresh_p='UNKNOWN full article; preview does not resolve',endpoints='Coverage/sharpness and reserve-relevant lower-bound violation proxy per public core',
 difference='Our declared task fixes commitment and scores actions via C/R/U/V; no exclusive novelty claim until full-text overlap is checked',
 missing='All inputs, pitch use, complete ablations and added decision analyses UNKNOWN',forbidden='No assertion full article has no pitch/history/action experiments; not a failing paper'),
dict(key='safer',id='L03',role='mainstream',version='Final publisher abstract plus author notebook source at3b0d501ce63425721c17d45cc76835af2846b24f; article PDF NOT obtained',online='UNKNOWN; DOI created2026-09-17 is not online date',read_scope='Final abstract and fixed public source cells2/23/25/27/29/31/33/35/37/57-58; source only; no outputs/measurements executed or retrieved',
 source_url='https://www.sciencedirect.com/science/article/pii/S2666546826002260',original='research_audit/reserve_allocation_paper_diligence_20261020/method_source/SAFER_code_cells.txt',
 knowledge='State-conditioned conformal recalibration with chronological evaluation, CQR/ACI comparators and moving-block inference; horizon-dependent mixed outcomes retained',
 power_history='Current generation allowed in source feature_cols; full processed lag/build clock not audited',state='State=f(season,intraday,current-generation bin); existing-information recoding; no measured pitch in read core',fresh_p='No measured-pitch vs equally fresh-P substitution in read main implementation',endpoints='Point accuracy; coverage/width/Winkler; conditional scores; DM/MBB',
 difference='Separate new measurement stream Z from f(I) and evaluate frozen reserve consequences; do not treat state recoding as new measurement',
 missing='Final PDF and agreement of all paper details with code unknown; no raw/processed input audit',forbidden='No first state-adaptive calibration; no claim lacks P/CQR/ACI; earlier SSRN is not final article'),
dict(key='wen2024',id='L04',role='mainstream',version='Energy2024 journal identity; author arXiv2305.14662v3 revised2024-04-24; 26 pages',online='UNKNOWN; Crossref created2024-05-07 not adopted as online',read_scope='Author v3 §§2-4,5-6; key inputs/missingness/metrics pp13-16; selected full-text not complete proof/code audit',
 source_url='https://arxiv.org/abs/2305.14662v3',original='literature_reading/wen2024_arxiv_v3.pdf',
 knowledge='Missingness-adaptive noncrossing quantile neural model without preprocessing/retraining; sporadic/block MCAR and self-masking MNAR',
 power_history='Six own-power lags; hourly WIND Toolkit2007-2013; 1-3h',state='Missingness indicators; not physical pitch labels or new pitch stream',fresh_p='No such pitch-substitution experiment in inspected case design',endpoints='Reliability; interval width; CRPS (§5.4)',
 difference='Frozen common commitment and separate measured/recovered-state additions; C/R/U/V rather than claiming a new missing-data forecaster',
 missing='Author manuscript not certified text-identical to final article; dataset values not verified',forbidden='No first missing telemetry/directQR/history baseline; synthetic missingness not field prevalence'),
dict(key='meng2026',id='L05',role='mainstream',version='PolyU final accepted manuscript; 12 pages; journal TSTE17(2)1202-1213 Apr2026',online='UNKNOWN in retrieved Crossref; created2025-09-25 not adopted as online',read_scope='Accepted manuscript §§II-IV, pp5-10 application/experiments; first page and pp6/8 visually checked; no author code/data',
 source_url='https://ira.lib.polyu.edu.hk/handle/10397/117725',original='literature_reading/meng2026_accepted.pdf',
 knowledge='End-to-end imputation and nonparametric probabilistic forecasting; multi-step recursive online imputation; MCAR5-50%; several modern baselines including AQR',
 power_history='Historical P sequence plus time-of-day/day-of-year; Willogoleche5min2018-2020;60/20/20 chronological split',state='Missing data reconstruction; not incremental measured pitch',fresh_p='No pitch vs equally fresh P experiment in inspected design',endpoints='Reliability deviation; interval width; skill score for1/6/12 steps (§IV-E)',
 difference='New-state measurement value after strong history/fixed forecast commitment, with reserve action consequences',
 missing='Accepted/final text identity and actual code preprocessing not independently verified',forbidden='No claim missingness/strong P sequence is unstudied or existing work only imputes independently'),
dict(key='stratigakos2026',id='L06',role='mainstream',version='UCL accepted author manuscript;12 pages; journal TSG17(1)806-817 Jan2026',online='2025-10-13 per publisher publication field; Crossref created same day',read_scope='§§II-V; pp6-11 experiment design/results and RMSE; pp7 visually checked; not code/data replication',
 source_url='https://discovery.ucl.ac.uk/id/eprint/10215885/1/Learning_Data-Driven_Uncertainty_Set_Partitions_for_Robust_and_Adaptive_Energy_Forecasting_with_Missing_Data.pdf',original='literature_reading/stratigakos2026_accepted.pdf',
 knowledge='Linear/neural adaptive robust forecasting and learned missing-feature partitions; Markov-persistent missingness; persistence forward-fill comparator',
 power_history='8plants x3 P times=24 potentially missing features + assumed always available hourly-production forecast issued6h before;15min-4h',state='Availability pattern and adaptive parameters; not measured pitch stream',fresh_p='Fresh vs missing P information explicit; no pitch alternative in inspected design',endpoints='MSE training/RMSE evaluation; model cost/partition sensitivity',
 difference='Physical-state additions and fixed shortfall-action endpoints rather than point-forecast robustness alone',
 missing='No field communication delay prevalence; old forecast operational availability is their assumption',forbidden='No first stale/continuous-missing information comparison; do not call this probabilistic forecasting study'),
dict(key='pritchard2011',id='L08',role='mainstream',version='Official free-to-read reader text and49mathGIFs retained locally; journal2011',online='2010-07-19 publisher PDF front matter; Crossref2011-03-14 conflict retained',read_scope='Existing complete reader+math-image record; this round selectively rechecked §§3-6, TablesIII/IV and conclusions; no independent formula reproduction',
 source_url='https://onlinelibrary.wiley.com/doi/10.1002/we.416',original='manuscripts/wind_energy/literature/fulltext/pritchard2011shortterm_with_formulas.html',
 knowledge='Current-power probabilistic persistence and richer quantile inputs; annual variation and distinct forecast properties; useful pressure/total-variation inputs',
 power_history='Present P plus optional power total-variation and extra inputs; current zero-P cases excluded; site wind speed unavailable',state='No explicit pitch comparison in read design',fresh_p='No pitch-vs-current-P alternative',endpoints='Quantile/probabilistic attributes; resolution vs sharpness',
 difference='Common old forecast commitment; measured/recovered-state and freshness alternatives; C/R/U/V and finite frozen-program scope',
 missing='Reader snapshot is not original publisher HTML/PDF; no global information redundancy proof',forbidden='No first current-power quantiles, limited benefit of added channels, or multiyear evaluation'),
dict(key='iversen2017',id='L09',role='mainstream',version='Author-hosted publisher version;12pages; online2016-05-02; journal2017',online='2016-05-02',read_scope='Full-text selected §§3.1/3.2,4 and TablesVI/VII; printed35-37/41-42; not all numerical implementation',
 source_url='https://henrikmadsen.org/wp-content/uploads/2017/05/leveraging_stochastic_wind_power.pdf',original='literature_reading/iversen2017.pdf',
 knowledge='SDE latent dynamics/dynamic power curve; compare observing P only vs P+wind speed; added measurement value decreases at longer horizons',
 power_history='Power observation/state filtering plus NWP; comparison changes observation stream',state='Latent wind/conversion states; optional measured wind speed; not measured pitch on strong P/Q history',fresh_p='Measurement addition studied but not pitch-vs-fresh-P replacement',endpoints='CRPS/energy score/MAE; out-of-sample year; not our paired reserve target',
 difference='Strong consequence histories followed by pitch/recovered-score and same-time P alternatives; fixed-commitment reserve C/R/U/V',
 missing='No causally identified sensor necessity; models differ under absent wind-speed observability',forbidden='No first comparison of extra measurement, latent-state recovery, or conditional information usefulness'),
dict(key='sophia2011',id='L10',role='foundational',version='Official publisher full-text HTML selected sections; journal2011',online='2010-12-13 official; author seminar PDF14Dec one-day difference retained in root note',read_scope='Root read abstract,§1,§2 consumer paradigm fragments,§3training criteria end,§4.1/4.2 and full§5; not all tables/math-images',
 source_url='https://onlinelibrary.wiley.com/doi/full/10.1002/we.444',original='ROOT_LITERATURE_CHECKS.csv (root reading-scope record; original remains official HTML)',
 knowledge='Forecast quality vs market value/reliability and conflicting end-user interests already studied; proposes training criterion on three farms',
 power_history='Full input/history not re-audited this round',state='Not used as state-specific exclusion proof',fresh_p='UNKNOWN beyond read sections',endpoints='Forecast quality and market value/reliability',
 difference='Concrete SCADA measurement/history/freshness contrasts; quality-versus-value is motivation, not new principle',
 missing='All numeric tables/formula figures not checked',forbidden='No first quality!=value or consequence-based evaluation'),
dict(key='phipps2022',id='L11',role='adjacent',version='KIT-hosted publisher PDF27pages; journal2022',online='2022-04-29',read_scope='Prior whole-PDF inclAppendixA reading record; this round selectively rechecked§3.2 and§§5-6; no exhaustive curve-pixel audit',
 source_url='https://publikationen.bibliothek.kit.edu/1000145553/149863404',original='manuscripts/wind_energy/literature/fulltext/phipps2022postprocessing.pdf',
 knowledge='Four post-processing placements with fixed forecasting recipes; established pipeline-comparison design',
 power_history='Weather-to-power ensemble pipeline; not our reserve-layer raw-input comparison',state='Post-processing placement rather than extra pitch stream',fresh_p='Not this comparison',endpoints='CRPS/calibration evaluation',
 difference='Change reserve-layer information after common commitment; evaluate C/R/U/V and declared statistical qualification',
 missing='No formal equivalence follows from similar point results; no runtime benefit transferred',forbidden='No first pipeline simplification; CRPS benefit not reserve benefit'),
dict(key='dantas2026',id='L12',role='adjacent',version='Glasgow publisher PDF19pages; online2025-12-25; journal2026',online='2025-12-25',read_scope='Prior19page full reading record; this round§§2-4 and test-year/horizon/theoretical-reference passages; independentSI not obtained',
 source_url='https://eprints.gla.ac.uk/359793/2/359793.pdf',original='manuscripts/wind_energy/literature/fulltext/dantas2026seamless.pdf',
 knowledge='Separate NWP uncertainty and weather-to-power uncertainty; quantify relative relevance across horizons, farms and years',
 power_history='NWP/weather-to-power probabilistic inputs; not reserve-layer SCADA after commonF',state='Uncertainty source modeling; not added physical pitch stream',fresh_p='Not this comparison',endpoints='CRPS and forecast calibration over73farms/5years',
 difference='Incremental downstream telemetry after fixed shared forecast; C/R/U/V; no claim first staged/cross-year study',
 missing='Test-period winner explicitly theoretical reference; cannot transfer as historical frozen selection',forbidden='No first uncertainty-source or multiyear comparison; no claiming equivalent scale'),
dict(key='zhao2021',id='L13',role='foundational',version='Verified journal identity; publisher abstract/method index only; fulltext NOT read',online='UNKNOWN; Crossref created2021-01-22 not adopted as online',read_scope='IEEE publisher abstract and method/section index plus Crossref; no full text',
 source_url='https://ieeexplore.ieee.org/document/9334448',original='research_audit/closest_literature_audit_20261019/literature_matrix.csv (source index only)',
 knowledge='Integrated prediction intervals and reserve decision optimization, procurement/shortage costs with coverage requirements',
 power_history='UNKNOWN detailed inputs',state='UNKNOWN complete state inputs',fresh_p='UNKNOWN',endpoints='Operating-reserve procurement/shortage cost and coverage (abstract scope)',
 difference='Common point-forecast commitment fixed before comparing added telemetry; not a claim to invent reserve-cost evaluation',
 missing='Complete inputs/ablations/auxiliary analyses unknown',forbidden='No first probabilistic-forecast-to-reserve link or new cost concept; no whole-article exclusion'),
dict(key='sun2022',id='L14',role='mainstream',version='Verified journal metadata and prior author-institution PDF selective reading',online='2022-06-24 Crossref online; issue label2022-05-01 retained',read_scope='Prior source selective-method notes; current retained printed036303-1,-2 abstract/introduction; no new full-article read',
 source_url='https://doi.org/10.1063/5.0087144',original='manuscripts/wind_energy/literature/READING_NOTES.md (scope log only)',
 knowledge='Error-distribution/reserve layer after existing median point forecasts with system production simulation',
 power_history='Existing common forecast plus contextual reserve layer; complete input chronology not re-audited',state='Not an exclusion proof about pitch measurement',fresh_p='UNKNOWN complete paper',endpoints='Dynamic reserve requirements and production-simulation consequences',
 difference='Specific incremental SCADA/degraded-information comparisons; our proxy is not their system economic simulation',
 missing='Full methods/runtime economics not rechecked this round',forbidden='No first post-forecast reserve interface; no transferring system-level savings'),
]

rows=[]
for d in DETAILS:
    m,p=meta(d['key'])
    row=dict(id=d['id'],title=m['title'][0],authors='; '.join(a.get('given','')+' '+a.get('family','') for a in m.get('author',[])),doi=m['DOI'],venue=m.get('container-title',[''])[0],volume=m.get('volume',''),issue=m.get('issue',''),pages_or_article=m.get('page',m.get('article-number','')),issue_date=dates(m,'published-print'),first_online=d['online'],crossref_created=dates(m,'created'),role=d['role'],version=d['version'],metadata_path=p,metadata_status='VERIFIED_RECORD; dates field-specific',source_url=d['source_url'],original_or_reading_index=d['original'],read_scope=d['read_scope'],existing_knowledge=d['knowledge'],power_history_and_clock=d['power_history'],state_or_measurement=d['state'],equally_fresh_P_comparison=d['fresh_p'],evaluated_endpoints=d['endpoints'],substantive_difference=d['difference'],unknown_or_boundary=d['missing'],forbidden_novelty_claim=d['forbidden'],audit_date='2026-10-20')
    rows.append(row)
pre=dict(id='L07',title='Marginalize, Rather than Impute: Probabilistic Wind Power Forecasting with Incomplete Data',authors='Honglin Wen; Pierre Pinson; Jie Gu; Zhijian Jin',doi='10.48550/arXiv.2403.03631',venue='arXiv; submitted to INFORMS Journal on Data Science',volume='',issue='',pages_or_article='25pages',issue_date='NOT_JOURNAL_PUBLICATION',first_online='v1 2024-03-06; v2 2025-12-03',crossref_created='DataCite arXiv DOI',role='adjacent',version='Author arXiv2403.03631v2; title differs from2024v1',metadata_path='https://arxiv.org/abs/2403.03631v2',metadata_status='VERIFIED_arXiv_version_record; peer-review acceptance UNKNOWN',source_url='https://arxiv.org/abs/2403.03631v2',original_or_reading_index='literature_reading/wen2025_arxiv_v2.pdf',read_scope='§§2,4-6; own/nearby history and metrics atpp15-20; selected full text; no source/data execution',existing_knowledge='Generative joint model conditions observed features and marginalizes unobserved features; compares own/neighbor histories',power_history_and_clock='WIND Toolkit2007-2013 hourly; own/nearby power histories; temporal80/20 split;1-3h',state_or_measurement='Latent generative variables and missingness; not incremental measured pitch',equally_fresh_P_comparison='No pitch-vs-equally-freshP design in inspected case study',evaluated_endpoints='Calibration; interval sharpness; CRPS',substantive_difference='Extra measured/recovered physical state after common commitment and strong history; reserve consequences',unknown_or_boundary='Preprint only in retrieved record; not final accepted article; no dataset/code audit',forbidden_novelty_claim='No first latent recovery/marginalization/incomplete-information forecast claim; do not cite oldv1title asv2',audit_date='2026-10-20')
rows.append(pre)
rows.sort(key=lambda r:r['id'])
with (OUT/'LITERATURE_MATRIX.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

provenance=[]
for p in (OUT/'literature_reading').glob('*'):
    if p.is_file():provenance.append(dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),purpose='literature_only_not_measurement_or_experiment'))
for p in ROOT.glob('*crossref*.json'):
    provenance.append(dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),purpose='registry_metadata'))
for p in [Path('1-s2.0-S2666827026001222-main.pdf'),Path('manuscripts/wind_energy/literature/fulltext/dantas2026seamless.pdf'),Path('manuscripts/wind_energy/literature/fulltext/phipps2022postprocessing.pdf'),Path('manuscripts/wind_energy/literature/fulltext/pritchard2011shortterm_with_formulas.html'),Path('research_audit/reserve_allocation_paper_diligence_20261020/method_source/SAFER_code_cells.txt')]:
    provenance.append(dict(path=str(p.resolve()),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),purpose='existing_primary_source_read_only'))
(ROOT/'PROVENANCE.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2),encoding='utf-8')

assert len(rows)==14
assert len({r['id'] for r in rows})==14
assert len({r['doi'].lower() for r in rows})==14
assert all(r['role'] in {'foundational','mainstream','failing','adjacent'} for r in rows)
assert all(r['read_scope'] and r['substantive_difference'] and r['unknown_or_boundary'] for r in rows)
print('14 literature rows; unique DOI/ID, allowed roles and explicit scope/boundary checked. No research calculation.')
