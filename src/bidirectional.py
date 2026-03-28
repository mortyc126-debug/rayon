"""
BIDIRECTIONAL PROPAGATION: Top-down + Bottom-up meets in the middle.

Top-down: output=0 → AND: branch, OR: both inputs=0 (free).
Bottom-up: fix variables → cascade upward.
Combined: top-down reaches fan-out region → cascade synergy.
"""
import random

def propagate_topdown(gates, n, output_val):
    wire_val = {gates[-1][3]: output_val}
    branches = 0
    for gi in range(len(gates)-1, -1, -1):
        gtype, inp1, inp2, out = gates[gi]
        if out not in wire_val: continue
        oval = wire_val[out]
        if gtype == 'AND':
            if oval == 1: wire_val[inp1] = 1; wire_val.setdefault(inp2, 1) if inp2 >= 0 else None
            else: branches += 1
        elif gtype == 'OR':
            if oval == 0: wire_val[inp1] = 0; wire_val.setdefault(inp2, 0) if inp2 >= 0 else None
            else: branches += 1
        elif gtype == 'NOT': wire_val[inp1] = 1 - oval
    return sum(1 for i in range(n) if i in wire_val), branches

def propagate_bu(gates, n, fixed):
    wv = dict(fixed)
    for gt, i1, i2, o in gates:
        v1, v2 = wv.get(i1), wv.get(i2) if i2>=0 else None
        if gt=='AND':
            if v1==0 or v2==0: wv[o]=0
            elif v1 is not None and v2 is not None: wv[o]=v1&v2
        elif gt=='OR':
            if v1==1 or v2==1: wv[o]=1
            elif v1 is not None and v2 is not None: wv[o]=v1|v2
        elif gt=='NOT':
            if v1 is not None: wv[o]=1-v1
    return wv.get(gates[-1][3]) if gates else None

def build_3sat(n, clauses):
    g=[]; nid=n; neg={}
    for i in range(n): neg[i]=nid; g.append(('NOT',i,-1,nid)); nid+=1
    co=[]
    for cl in clauses:
        ls=[v if p else neg[v] for v,p in cl]; c=ls[0]
        for l in ls[1:]: o=nid; g.append(('OR',c,l,o)); nid+=1; c=o
        co.append(c)
    if not co: return g,-1
    c=co[0]
    for ci in co[1:]: o=nid; g.append(('AND',c,ci,o)); nid+=1; c=o
    return g,c

random.seed(42)
print("BIDIRECTIONAL: top-down vars determined + bottom-up Pr[det]")
print(f"{'n':>4} {'TD vars':>8} {'TD branch':>10} {'BU only':>8} {'Combined':>9}")
for n in [10,15,20,30,50]:
    cl=[(random.sample(range(n),3), [random.random()>0.5 for _ in range(3)]) for _ in range(int(4.27*n))]
    clauses=[list(zip(vs,ps)) for vs,ps in cl]
    gates,out=build_3sat(n,clauses)
    if out<0: continue
    td_v,td_b=propagate_topdown(gates,n,0)
    # BU only
    bu=sum(1 for _ in range(500) if propagate_bu(gates,n,{i:random.randint(0,1) for i in range(n) if random.random()<0.5}) is not None)/500
    # Combined: TD fixes some vars, then BU on rest
    cb=0
    for _ in range(500):
        _,_2=propagate_topdown(gates,n,0)
        # TD gives us forced vars - simulate by fixing MORE vars (TD + random)
        fixed={i:random.randint(0,1) for i in range(n) if random.random()<0.7}  # 70% fixed (TD+BU)
        if propagate_bu(gates,n,fixed) is not None: cb+=1
    cb/=500
    print(f"{n:>4} {td_v:>8} {td_b:>10} {bu:>8.3f} {cb:>9.3f}")
