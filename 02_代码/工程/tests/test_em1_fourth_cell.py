import numpy as np
import pytest
from scripts.run_em1_fourth_cell import fourth_actions,ROLE,PAIRS

def test_family_pair_schema():
 assert ROLE=='D_ALPHA_ALL_TREE_Z'
 assert PAIRS==[(ROLE,'EM1_007_Z'),('EM1_008_Z',ROLE),('NV_MAJOR_Z','EM1_007_Z')]

def test_zero_fit_tree_routed_global_alpha_and_timing():
 class T:
  def apply(self,x):return (x[:,0]>0).astype(int)
 a=np.array([29383,29384,29815,29816,30239,30240])
 safe=np.full((6,2),10.);cost=np.full((6,2),20.);x=np.zeros((6,2,5));x[:,1,0]=1
 t={s:T() for s in ['C','E','D']};p={s:{'alpha_all':v,'leaf_alphas':{'0':0.,'1':v},'release_leaf':1} for s,v in zip(['C','E','D'],[.2,.4,.8])}
 out,route=fourth_actions(dict(anchors=a,safe=safe,cost=cost,current_features=x),t,p)
 np.testing.assert_array_equal(route[:,0],[-1,0,0,0,0,0])
 np.testing.assert_allclose(out[:,1],[10,12,12,14,14,18])
 assert np.isfinite(out).all()

def test_action_view_never_exposes_targets():
 from scripts.run_em1_fourth_cell import action_view
 class M(dict):
  def __getitem__(self,k):
   if k in ('shortfall','mask'):raise AssertionError(k)
   return super().__getitem__(k)
 b=M(anchors=np.array([1]),safe=np.ones((1,1)),cost=np.ones((1,1)),current_features=np.zeros((1,1,5)),shortfall=None,mask=None)
 assert set(action_view(b))=={'anchors','safe','cost','current_features'}

def test_bad_coefficient_refused():
 class T:
  def apply(self,x):return np.zeros(len(x),dtype=int)
 b=dict(anchors=np.array([29384]),safe=np.ones((1,1)),cost=np.ones((1,1)),current_features=np.zeros((1,1,5)))
 p={s:{'alpha_all':-1,'leaf_alphas':{'0':0}} for s in ['C','E','D']}
 with pytest.raises(ValueError):fourth_actions(b,{s:T() for s in p},p)


class _FixedTree:
 def __init__(self):
  from types import SimpleNamespace
  self.tree_=SimpleNamespace(children_left=np.array([1,-1,-1]),children_right=np.array([2,-1,-1]),feature=np.array([0,-2,-2]),threshold=np.array([1.,-2.,-2.]))
 def apply(self,x):return np.where(np.asarray(x,dtype=np.float32)[:,0]<=1.,1,2)


def _receipts(alpha=.25,support=(9,1)):
 common=dict(status='FITTED_OK',fallback_to_safe=False,seed=201,arm='Z',vintage='outer',snapshot='C',cut_anchor=29376,enabled_anchor=29384,episode_start=29384,valid_row_sha256='fixed',selected_issue_count=432,valid_fit_cells=sum(support))
 return dict(common,alpha=alpha,global_fit_stats={'alpha':alpha}),dict(common,leaf_stats={'1':{'n_cells':support[0]},'2':{'n_cells':support[1]}},leaf_alphas={'1':.5,'2':0.})


def _inputs(tmp_path,alphas=(.2,.4,.8)):
 from scripts import run_em1_fourth_cell as r
 parameters={};paths={};trees={}
 for (snap,(cut,start,_)),alpha in zip(r.SNAPS.items(),alphas):
  a,g=_receipts(alpha)
  for obj in (a,g):obj.update(snapshot=snap,cut_anchor=cut,enabled_anchor=start,episode_start=start)
  tree=_FixedTree();trees[snap]=tree;parameters[snap]=r.freeze_parameters(a,g,tree)
  paths[snap]=tmp_path/f'{snap}.json';r.save_new(paths[snap],parameters[snap])
 a=np.array([29383,29384,29815,29816,30239,30240]);safe=np.full((6,2),10.);cost=np.full_like(safe,20.);features=np.zeros((*safe.shape,5));features[:,1,0]=2.
 return dict(anchors=a,safe=safe,cost=cost,current_features=features),parameters,paths,trees


def test_manual_node_reconstruction_matches_tree_apply(tmp_path):
 from scripts import run_em1_fourth_cell as r
 bank,p,paths,trees=_inputs(tmp_path);out,route=r.fourth_actions(bank,trees,p)
 rebuilt,manual,choice=r.independent_module().independent_actions(bank,paths)
 assert out.tobytes()==rebuilt.tobytes() and np.array_equal(route,manual)
 np.testing.assert_array_equal(out[:,0],[10,12,12,14,14,18]);np.testing.assert_array_equal(out[:,1],[10]*6)
 assert [choice[s]['alpha'] for s in r.SNAPS]==[.2,.4,.8]


def test_float32_routing_at_double_precision_boundary(tmp_path):
 from scripts import run_em1_fourth_cell as r
 bank,p,paths,trees=_inputs(tmp_path);bank['current_features'][:,1,0]=1.+2**-25
 out,route=r.fourth_actions(bank,trees,p);rebuilt,manual,_=r.independent_module().independent_actions(bank,paths)
 assert out.tobytes()==rebuilt.tobytes() and np.array_equal(route,manual) and route[-1,1]==1


def test_alpha_one_uses_original_gate_floating_arithmetic(tmp_path):
 from scripts import run_em1_fourth_cell as r
 bank,p,paths,trees=_inputs(tmp_path,(1.,1.,1.));bank['safe'][:]=1e16;bank['cost'][:]=1.
 out,_=r.fourth_actions(bank,trees,p);assert out[-1,0]==0. and out[-1,1]==1e16
 rebuilt,_,_=r.independent_module().independent_actions(bank,paths);assert out.tobytes()==rebuilt.tobytes()


def test_alpha_zero_instance_kept_with_its_route(tmp_path):
 from scripts import run_em1_fourth_cell as r
 bank,p,paths,trees=_inputs(tmp_path,(0.,0.,0.));out,route=r.fourth_actions(bank,trees,p)
 assert np.array_equal(out,bank['safe']) and (route[-1]>=0).all()


@pytest.mark.parametrize('alpha',[np.nan,np.inf,-.01,1.01])
def test_frozen_alpha_domain(alpha):
 from scripts import run_em1_fourth_cell as r
 a,g=_receipts(alpha)
 with pytest.raises(ValueError,match='alpha'):r.freeze_parameters(a,g,_FixedTree())


def test_source_training_rows_and_veto_branch_checked():
 from scripts import run_em1_fourth_cell as r
 a,g=_receipts();g['valid_row_sha256']='different'
 with pytest.raises(ValueError,match='training identity'):r.freeze_parameters(a,g,_FixedTree())
 a,g=_receipts();g['leaf_alphas']['2']=.1
 with pytest.raises(ValueError,match='release branch'):r.freeze_parameters(a,g,_FixedTree())


def test_tied_historical_support_uses_smallest_leaf():
 from scripts import run_em1_fourth_cell as r
 a,g=_receipts(support=(5,5));g['leaf_stats']={'2':{'n_cells':5},'1':{'n_cells':5}}
 p=r.freeze_parameters(a,g,_FixedTree());assert p['release_leaf']==1 and p['leaf_alphas']['1']==.25


def test_independent_daily_formula_on_hand_calculated_example():
 from scripts import run_em1_fourth_cell as r
 d,n,days=r.independent_module().independent_daily(np.array([[6.,12.],[3.,6.]]),np.array([[12.,12.],[6.,1.]]),np.array([[True,True],[True,False]]),np.array([144,288]))
 np.testing.assert_array_equal(d,[[13.,3.,1.,1.],[5.5,.5,.5,1.]])
 np.testing.assert_array_equal(n,[2,1]);np.testing.assert_array_equal(days,[1,2])


def test_real_complete_parent_family_and_actual_coordinate_count():
 from pathlib import Path
 from scripts import run_em1_fourth_cell as r
 h=Path(__file__).resolve().parents[1]/'experiments/em1_minimal_followup_20261025/recovered/results/campaign/step2'
 info=r.read(h/'all_policy_names.json');names,a,p,x=r.extended_family(info)
 assert names[:-1]==info['names'] and a[:-1]==info['available'] and p[:-3]==[tuple(i) for i in info['comparisons']] and x==[tuple(i) for i in info['aliases']]
 assert (len(names),len(p),len(x))==(1402,7263,152)
 assert r.N_COORDINATES==88011+11+3*10==11*1402+10*7263==88052


def test_original_204_positive_global_coefficient_receipt():
 from pathlib import Path
 from scripts import run_em1_fourth_cell as r
 h=Path(__file__).resolve().parents[1]/'experiments/endpoint_match_20261025/recovered/results/campaign/models/outer/E/Z_seed204'
 a=r.read(h/'EM007_receipt.json');g=r.read(h/'EM008_receipt.json');p=r.freeze_parameters(a,g,_FixedTree())
 assert p['alpha_all']==.05332232809187814 and p['leaf_alphas']['1']!=g['leaf_alphas']['1']


def test_missing_seed_and_changed_freeze_barrier_rejected(tmp_path):
 from scripts import run_em1_fourth_cell as r
 cfg={'source_hashes':{'x':'y'}};r.save_new(tmp_path/'protocol_original.json',cfg)
 r.save_new(tmp_path/'FINAL_FREEZE.json',dict(seeds={},source_hashes=cfg['source_hashes'],protocol_sha256=r.sha(tmp_path/'protocol_original.json'),evaluation_touched=False))
 r.save_new(tmp_path/'EVALUATION_OPEN.json',dict(freeze_sha256=r.sha(tmp_path/'FINAL_FREEZE.json'),protocol_sha256=r.sha(tmp_path/'protocol_original.json'),source_hashes=cfg['source_hashes']))
 with pytest.raises(ValueError,match='five historical instances'):r.verified_freeze(cfg,tmp_path)
 with (tmp_path/'FINAL_FREEZE.json').open('ab') as stream:stream.write(b' ')
 with pytest.raises(ValueError,match='opening barrier'):r.verified_freeze(cfg,tmp_path)


def test_scientific_output_refuses_overwrite(tmp_path):
 from scripts import run_em1_fourth_cell as r
 p=tmp_path/'receipt.json';r.save_new(p,{'frozen':True})
 with pytest.raises(FileExistsError):r.save_new(p,{'frozen':False})


def test_deployed_root_source_archive_is_bound_to_pbs_identity(tmp_path,monkeypatch):
 from scripts import run_em1_fourth_cell as r
 (tmp_path/'producer.py').write_text('frozen source')
 (tmp_path/'source_payload.zip').write_bytes(b'immutable deployed archive')
 cfg={'source_hashes':{'producer.py':r.sha(tmp_path/'producer.py')}}
 monkeypatch.setattr(r,'ROOT',tmp_path)
 monkeypatch.setenv('CAMPAIGN_RELEASE',r.sha(tmp_path/'source_payload.zip'))
 r.source_check(cfg)
 monkeypatch.setenv('CAMPAIGN_RELEASE','different archive')
 with pytest.raises(ValueError,match='archive identity'):r.source_check(cfg)


def test_frozen_model_source_leaf_route_equals_d_and_manual_route(tmp_path):
 from scripts import run_em1_fourth_cell as r
 bank,p,paths,trees=_inputs(tmp_path)
 _,route=r.fourth_actions(bank,trees,p)
 _,manual,_=r.independent_module().independent_actions(bank,paths)
 source=np.full(route.shape,-1,dtype=np.int64)
 for snap,(_,lo,hi) in r.SNAPS.items():
  sel=(bank['anchors']>=lo)&(bank['anchors']<hi)
  source[sel]=trees[snap].apply(bank['current_features'][sel].reshape(-1,5)).reshape(source[sel].shape)
 np.testing.assert_array_equal(source,route);np.testing.assert_array_equal(source,manual)
