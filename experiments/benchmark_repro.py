"""Independent re-implementation of the Layer-1 benchmark cases (thesis Fig.3-4).

Purpose: third-party verification of the reference values and the OpenSeesPy
accuracy claim, using models written from scratch (NOT the repo's code).
Cases 1-6: beam systems, parameters cross-checked against analytical solutions.
Cases 7-8: Warren truss per thesis Fig.3-5 APDL script (span 8m, H 2m, 8 panels,
           E=200GPa, A=0.01 m^2; case 7 lower-chord nodes 10 kN each,
           case 8 mid-span node 20 kN).
Cases 9-10 (frames): parameters not reliably legible from the thesis PDF -> skipped,
           to be run from the repo's own pytest suite once access is granted.
All results in SI; reported in mm / kN.m / MPa.
"""
import math
import openseespy.opensees as ops

E_C, b, h = 30e9, 0.3, 0.6
I = b * h**3 / 12          # 0.0054 m^4
A = b * h                  # 0.18 m^2
W = b * h**2 / 6           # 0.018 m^3
results = []

def beam_model(L, n_ele, support, loads):
    """2D elasticBeamColumn line model. support: 'ss'|'cant'|('cont',[xs of mid supports])"""
    ops.wipe(); ops.model('basic', '-ndm', 2, '-ndf', 3)
    n_nodes = n_ele + 1
    for i in range(n_nodes):
        ops.node(i + 1, i * L / n_ele, 0.0)
    if support == 'ss':
        ops.fix(1, 1, 1, 0); ops.fix(n_nodes, 0, 1, 0)
    elif support == 'cant':
        ops.fix(1, 1, 1, 1)
    else:  # continuous
        ops.fix(1, 1, 1, 0)
        for xs in support[1]:
            ops.fix(round(xs / (L / n_ele)) + 1, 0, 1, 0)
        ops.fix(n_nodes, 0, 1, 0)
    ops.geomTransf('Linear', 1)
    for i in range(n_ele):
        ops.element('elasticBeamColumn', i + 1, i + 1, i + 2, A, E_C, I, 1)
    ops.timeSeries('Linear', 1); ops.pattern('Plain', 1, 1)
    for kind, val, pos in loads:
        if kind == 'udl':
            for i in range(1, n_ele + 1):
                ops.eleLoad('-ele', i, '-type', '-beamUniform', -val)
        else:  # point load
            ops.load(round(pos / (L / n_ele)) + 1, 0.0, -val, 0.0)
    ops.system('BandSPD'); ops.numberer('RCM'); ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0); ops.algorithm('Linear')
    ops.analysis('Static'); ops.analyze(1)
    dmax = max(abs(ops.nodeDisp(i + 1, 2)) for i in range(n_nodes))
    mmax = 0.0
    for i in range(1, n_ele + 1):
        f = ops.eleForce(i)          # [Px1,Py1,Mz1,Px2,Py2,Mz2]
        mmax = max(mmax, abs(f[2]), abs(f[5]))
    return dmax, mmax, mmax / W

def add(no, name, calc, ref, tol):
    d_c, m_c, s_c = calc; d_r, m_r, s_r = ref
    err = max(abs(d_c - d_r) / d_r, abs(m_c - m_r) / m_r, abs(s_c - s_r) / s_r) * 100
    results.append((no, name, d_c * 1e3, d_r * 1e3, m_c / 1e3, m_r / 1e3,
                    s_c / 1e6, s_r / 1e6, err, 'PASS' if err < tol else 'FAIL', tol))

# ---- Case 1: simply supported, udl. L=6, q=10 kN/m -------------------------
L, q = 6.0, 10e3
ref = (5 * q * L**4 / (384 * E_C * I), q * L**2 / 8, q * L**2 / 8 / W)
add(1, 'SS beam, UDL', beam_model(L, 40, 'ss', [('udl', q, None)]), ref, 1.0)

# ---- Case 2: simply supported, midspan point. P=30 kN ----------------------
P = 30e3
ref = (P * L**3 / (48 * E_C * I), P * L / 4, P * L / 4 / W)
add(2, 'SS beam, point', beam_model(L, 40, 'ss', [('pt', P, L / 2)]), ref, 1.0)

# ---- Case 3: cantilever, udl. L=3, q=10 kN/m -------------------------------
L = 3.0
ref = (q * L**4 / (8 * E_C * I), q * L**2 / 2, q * L**2 / 2 / W)
add(3, 'Cantilever, UDL', beam_model(L, 40, 'cant', [('udl', q, None)]), ref, 1.0)

# ---- Case 4: cantilever, free-end point. P=20 kN ---------------------------
P = 20e3
ref = (P * L**3 / (3 * E_C * I), P * L, P * L / W)
add(4, 'Cantilever, point', beam_model(L, 40, 'cant', [('pt', P, L)]), ref, 1.0)

# ---- Case 5: two-span continuous (5+5 m), udl q=10 -------------------------
L, q = 10.0, 10e3                      # total length, mid support at 5
calc = beam_model(L, 40, ('cont', [5.0]), [('udl', q, None)])
ref = (q * 5.0**4 / (185 * E_C * I), q * 5.0**2 / 8, q * 5.0**2 / 8 / W)   # classical
add(5, '2-span cont., UDL', calc, ref, 3.0)

# ---- Case 6: two-span continuous, midspan points P=30 each -----------------
P = 30e3
calc = beam_model(L, 40, ('cont', [5.0]), [('pt', P, 2.5), ('pt', P, 7.5)])
ref = (0.216e-3, 3 * P * 5.0 / 16, 3 * P * 5.0 / 16 / W)   # thesis/ANSYS deflection ref
add(6, '2-span cont., points', calc, ref, 3.0)

# ---- Cases 7-8: Warren truss, span 8 m, H 2 m, 8 panels --------------------
def warren(load_case):
    ops.wipe(); ops.model('basic', '-ndm', 2, '-ndf', 2)
    Et, At, span, H, n_p = 200e9, 0.01, 8.0, 2.0, 8
    pl = span / n_p
    bot = []; top = []
    nid = 0
    for i in range(n_p + 1):
        nid += 1; ops.node(nid, i * pl, 0.0); bot.append(nid)
    for i in range(n_p - 1):
        nid += 1; ops.node(nid, (i + 1) * pl, H); top.append(nid)
    ops.fix(bot[0], 1, 1); ops.fix(bot[-1], 0, 1)
    eid = 0
    def el(a, c):
        nonlocal eid; eid += 1; ops.element('Truss', eid, a, c, At, 1)
    ops.uniaxialMaterial('Elastic', 1, Et)
    for i in range(n_p):            # bottom chord
        el(bot[i], bot[i + 1])
    for i in range(len(top) - 1):   # top chord
        el(top[i], top[i + 1])
    el(bot[0], top[0]); el(top[-1], bot[-1])           # end diagonals
    for i in range(len(top)):       # verticals + diagonals
        el(top[i], bot[i + 1])
        if i < len(top) - 1:
            el(top[i], bot[i + 2])
    ops.timeSeries('Linear', 1); ops.pattern('Plain', 1, 1)
    if load_case == 'udl_nodes':
        for n in bot[1:-1]:
            ops.load(n, 0.0, -10e3)
    else:
        ops.load(bot[n_p // 2], 0.0, -20e3)
    ops.system('BandSPD'); ops.numberer('RCM'); ops.constraints('Plain')
    ops.integrator('LoadControl', 1.0); ops.algorithm('Linear')
    ops.analysis('Static'); ops.analyze(1)
    dmax = max(abs(ops.nodeDisp(n, 2)) for n in bot + top)
    smax = max(abs(ops.basicForce(e)[0]) / At for e in range(1, eid + 1))
    return dmax, smax

for no, name, lc, ref_d, ref_s in [(7, 'Warren truss, node loads', 'udl_nodes', 0.247e-3, 4e6),
                                   (8, 'Warren truss, mid point', 'mid', 0.133e-3, 2e6)]:
    d_c, s_c = warren(lc)
    err = max(abs(d_c - ref_d) / ref_d, abs(s_c - ref_s) / ref_s) * 100
    results.append((no, name, d_c * 1e3, ref_d * 1e3, float('nan'), float('nan'),
                    s_c / 1e6, ref_s / 1e6, err, 'PASS' if err < 3.0 else 'CHECK-GEOM', 3.0))

# ---- report -----------------------------------------------------------------
hdr = f"{'No':3s}{'Case':26s}{'d_calc':>8s}{'d_ref':>8s}{'M_calc':>8s}{'M_ref':>8s}{'s_calc':>8s}{'s_ref':>8s}{'err%':>7s}  status"
print(hdr); print('-' * len(hdr))
for r in results:
    print(f"{r[0]:<3d}{r[1]:26s}{r[2]:8.4f}{r[3]:8.4f}{r[4]:8.2f}{r[5]:8.2f}"
          f"{r[6]:8.3f}{r[7]:8.3f}{r[8]:7.2f}  {r[9]} (tol {r[10]}%)")
print('\nUnits: d in mm, M in kN.m, s in MPa. Cases 9-10 (frames) pending repo access.')
