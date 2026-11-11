"""Outcome-blind candidate factory and complete comparison responsibilities."""
import collections
import numpy as np


def recipes_for_loop(planned_old,completed_old,outer_ids):
    recipes=[]
    def add(**row):recipes.append(dict(id=len(recipes),**row))
    for goal in ['COST','CAP']:
        for kind in ['control_exact','control_fixed','control_ew']:
            add(kind=kind,goal=goal,family='controls')
    for eta in [.03,.3,3.,30.]:
        for power in [0.,.5,1.]:
            add(kind='actual',goal='COST',family='actual_cost',
                config=dict(eta=eta,schedule_power=power,severity_step=0.,cost_scale=100.))
    for eta in [.03,.3,3.,30.]:
        for power in [0.,.5,1.]:
            for step in [.1,1.,10.]:
                add(kind='actual',goal='CAP',family='actual_u',
                    config=dict(eta=eta,schedule_power=power,severity_step=step,cost_scale=100.))
    seen={r['recipe']['recipe_id'] for r in completed_old}
    buckets=collections.defaultdict(list)
    for old in planned_old:
        if old['recipe_id'] not in seen:
            if old['family']!='dual':raise ValueError('Unrun source is not the declared dual pool')
            c=old['config'];buckets[c['discount'],c['dual_eta_u'],old['prior']].append(old)
    coverage=[]
    while len(coverage)<128:
        changed=False
        for key in sorted(buckets):
            if buckets[key]:coverage.append(buckets[key].pop(0));changed=True
            if len(coverage)==128:break
        if not changed:raise ValueError('Insufficient outcome-blind source candidates')
    for old in coverage:add(kind='legacy',family='coverage',legacy=old)
    ref=next(r for r in completed_old if r['recipe'].get('prior')=='expert_0')
    reference=np.asarray(ref['metrics'])
    def distance(row):
        values=np.asarray(row['metrics'])
        severity=max(0.,float(np.max(10*(values[:,:,2]-reference[:,:,2])/100)))
        risk=max(0.,float(np.max(values[:,:,3])-.1))
        return (severity+risk,float(values[:,:,0].mean()),row['recipe']['recipe_id'])
    for family in ['simple','dual']:
        pool=[r for r in completed_old if r['recipe']['family']==family
              and r['recipe']['recipe_id'] not in outer_ids and r['status']=='COMPLETED']
        chosen=sorted(pool,key=distance)[:8]
        if len(chosen)!=8:raise ValueError('Insufficient protection representatives')
        for row in chosen:add(kind='legacy',family='protection',legacy=row['recipe'])
    assert len(recipes)==198
    keys=[r.get('legacy',{}).get('recipe_id') for r in recipes if r['kind']=='legacy']
    if len(set(keys))!=len(keys):raise ValueError('Duplicate source programs')
    return recipes


def comparison_family(recipes,parent):
    names=list(parent['policy_names']);pairs=[tuple(p) for p in parent['comparisons']]
    aliases=[tuple(p) for p in parent['aliases']]
    controls={(r['goal'],r['kind']):r['id'] for r in recipes if r['family']=='controls'}
    def name(i,arm):return f'R{i:04d}_{arm}'
    for r in recipes:
        names.extend([name(r['id'],'P'),name(r['id'],'Z')])
        pairs.append((name(r['id'],'Z'),name(r['id'],'P')))
        if r['kind']=='legacy' and r['legacy']['kind']=='calibration' and r['legacy']['base_index']==0:
            aliases.append((name(r['id'],'Z'),name(r['id'],'P')))
        if r['kind']=='actual':
            for arm in ['P','Z']:
                for base in ['control_exact','control_fixed','control_ew']:
                    pairs.append((name(r['id'],arm),name(controls[r['goal'],base],arm)))
        elif r['kind']=='legacy':
            goal='CAP' if r['family']=='protection' else 'COST'
            for arm in ['P','Z']:
                pairs.append((name(r['id'],arm),name(controls[goal,'control_exact'],arm)))
    for goal in ['COST','CAP']:
        for arm in ['P','Z']:
            pairs.append((name(controls[goal,'control_ew'],arm),name(controls[goal,'control_fixed'],arm)))
            pairs.append((name(controls[goal,'control_fixed'],arm),name(controls[goal,'control_exact'],arm)))
    if len(names)!=len(set(names)) or len(pairs)!=len(set(pairs)):
        raise ValueError('Duplicate names or comparison duties')
    return dict(names=names,comparisons=pairs,aliases=aliases,
        nominal_family_size=11*len(names)+10*len(pairs))
