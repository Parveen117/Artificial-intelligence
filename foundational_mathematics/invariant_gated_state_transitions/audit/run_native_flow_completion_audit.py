#!/usr/bin/env python3
from fractions import Fraction as F
import itertools
import json
import random
from pathlib import Path

SEED = 20260825
rng = random.Random(SEED)


def dot(a, b):
    return sum((x * y for x, y in zip(a, b)), F(0))


def transpose(A):
    return [list(c) for c in zip(*A)] if A else []


def matmul(A, B):
    BT = transpose(B)
    return [[dot(r, c) for c in BT] for r in A]


def matvec(A, x):
    return [dot(r, x) for r in A]


def matsub(A, B):
    return [[x - y for x, y in zip(ra, rb)] for ra, rb in zip(A, B)]


def matadd(A, B):
    return [[x + y for x, y in zip(ra, rb)] for ra, rb in zip(A, B)]


def scalemat(a, A):
    return [[a * x for x in row] for row in A]


def diag(vals):
    n = len(vals)
    return [[vals[i] if i == j else F(0) for j in range(n)] for i in range(n)]


def eye(n):
    return diag([F(1)] * n)


def rank(A):
    M = [list(map(F, row)) for row in A]
    if not M:
        return 0
    m, n = len(M), len(M[0])
    r = 0
    for c in range(n):
        p = next((i for i in range(r, m) if M[i][c]), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]
        piv = M[r][c]
        M[r] = [x / piv for x in M[r]]
        for i in range(m):
            if i != r and M[i][c]:
                q = M[i][c]
                M[i] = [x - q * y for x, y in zip(M[i], M[r])]
        r += 1
        if r == m:
            break
    return r


def qform(M, x):
    return dot(x, matvec(M, x))


def opnorm_diag(M):
    return max((abs(M[i][i]) for i in range(len(M))), default=F(0))


def frob2(M):
    return sum((x * x for row in M for x in row), F(0))


def exp_nilpotent(G, t):
    n = len(G)
    out = eye(n)
    P = eye(n)
    tk = F(1)
    fact = 1
    for k in range(1, n + 1):
        P = matmul(P, G)
        tk *= t
        fact *= k
        out = matadd(out, scalemat(tk / F(fact), P))
    return out


def rowvec_mat(r, A):
    return [dot(r, c) for c in transpose(A)]


results = {}


def record(name, count, status="PASS"):
    results[name] = {"trials": count, "status": status}


ROOT = Path(__file__).resolve().parents[1]
paper = ROOT / "paper"
src = (paper / "main.tex").read_text()
for q in sorted((paper / "sections").glob("*.tex")):
    src += "\n" + q.read_text()
for token in (
    "T14: positive-form carrier completion",
    "T15: bilateral flow and monotone observer-jet recognition",
    "T16: recognition-complete operator limit",
    "T17: no-hidden-memory completion",
    "T18: minimal observer and variational tail",
    "T19: exact infinite-to-finite inertia and margin",
    "T20: finite matrix convergence and outward promotion",
    "u_n+e_n<1",
):
    assert token in src
for forbidden in (
    "Riemann hypothesis",
    "Recognition Kernel Framework",
    "Recognition-Seam",
    "Madhava",
    "Smriti",
):
    assert forbidden not in src
record("Static theorem and term contracts", 8)

# T14: q(x)=||Dx||^2. Every q-bounded descended map has row space inside D.
for _ in range(5000):
    n = rng.randint(2, 8)
    r = rng.randint(1, n)
    D = [[F(int(i == j)) for j in range(n)] for i in range(r)]
    for i in range(r):
        for j in range(r, n):
            D[i][j] = F(rng.randint(-3, 3))
    W = [[F(rng.randint(-3, 3)) for _ in range(r)] for __ in range(rng.randint(1, 5))]
    T = matmul(W, D)
    assert rank(D) == r
    assert rank(D + T) == r
    if n > r:
        z = [F(0)] * n
        j = n - 1
        z[j] = F(1)
        for i in range(r):
            z[i] = -D[i][j]
        assert all(v == 0 for v in matvec(D, z))
        assert all(v == 0 for v in matvec(T, z))
record("T14 positive-form quotient/descended-map fixtures", 5000)

for _ in range(1000):
    n = rng.randint(2, 8)
    r = rng.randint(1, n - 1)
    D = [[F(int(i == j)) for j in range(n)] for i in range(r)]
    z = [F(0)] * n
    z[-1] = F(1)
    T = [[F(0)] * n]
    T[0][-1] = F(1)
    assert all(v == 0 for v in matvec(D, z))
    assert matvec(T, z)[0] != 0
record("T14 null-direction necessity controls", 1000, "PASS_NEGATIVE_CONTROL")

# T15: exact rational nilpotent bilateral flow and nested observer jets.
for _ in range(8000):
    n = rng.randint(2, 8)
    J = diag([F(1 if i % 2 == 0 else -1) for i in range(n)])
    G = [[F(0) for _ in range(n)] for __ in range(n)]
    for i in range(n - 1):
        G[i][i + 1] = F(rng.choice([1, 2, 3]))
    assert matmul(matmul(J, G), J) == scalemat(F(-1), G)
    B = [[F(1)] + [F(0)] * (n - 1)]
    assert matmul(B, J) == B
    t = F(rng.randint(1, 5), rng.randint(1, 5))
    U = exp_nilpotent(G, t)
    assert matmul(matmul(J, U), J) == exp_nilpotent(G, -t)

    previous_kernel_dim = n + 1
    P = eye(n)
    stack = []
    for k in range(n):
        if k > 0:
            P = matmul(P, G)
        row = matmul(B, P)[0]
        assert rowvec_mat(row, J) == [((-1) ** k) * x for x in row]
        stack.append(row)
        kernel_dim = n - rank(stack)
        assert kernel_dim <= previous_kernel_dim
        previous_kernel_dim = kernel_dim

    approx = B
    P = eye(n)
    tk = F(1)
    fact = 1
    for k in range(1, n):
        P = matmul(P, G)
        tk *= t
        fact *= k
        approx = matadd(approx, scalemat(tk / F(fact), matmul(B, P)))
    assert approx == matmul(B, U)
record("T15 bilateral flow / jet parity / exact nilpotent reconstruction", 8000)

for _ in range(1000):
    n = rng.randint(2, 7)
    J = eye(n)
    G = [[F(0) for _ in range(n)] for __ in range(n)]
    for i in range(n - 1):
        G[i][i + 1] = F(1)
    assert matmul(matmul(J, G), J) != scalemat(F(-1), G)
    t = F(1, 2)
    U = exp_nilpotent(G, t)
    assert matmul(matmul(J, U), J) != exp_nilpotent(G, -t)
record("T15 wrong-involution bilateral controls", 1000, "PASS_NEGATIVE_CONTROL")

# T16: exact diagonal operator-norm Gram bounds.
for _ in range(8000):
    d = rng.randint(1, 8)
    y = [F(rng.randint(-5, 5)) for _ in range(d)]
    m = [F(rng.randint(-5, 5)) for _ in range(d)]
    nidx = rng.randint(2, 50)
    dy = [F(rng.randint(-3, 3), nidx) for _ in range(d)]
    dm = [F(rng.randint(-3, 3), nidx) for _ in range(d)]
    yn = [a + b for a, b in zip(y, dy)]
    mn = [a + b for a, b in zip(m, dm)]
    Y, Yn, M, Mn = diag(y), diag(yn), diag(m), diag(mn)
    R, Rn = matmul(transpose(Y), Y), matmul(transpose(Yn), Yn)
    D, Dn = matmul(transpose(M), M), matmul(transpose(Mn), Mn)
    Fs, Fsn = matsub(R, D), matsub(Rn, Dn)
    drec = max((abs(v) for v in dy), default=F(0))
    dmem = max((abs(v) for v in dm), default=F(0))
    normY = max((abs(v) for v in y), default=F(0))
    normYn = max((abs(v) for v in yn), default=F(0))
    normM = max((abs(v) for v in m), default=F(0))
    normMn = max((abs(v) for v in mn), default=F(0))
    assert opnorm_diag(matsub(R, Rn)) <= (normY + normYn) * drec
    assert opnorm_diag(matsub(D, Dn)) <= (normM + normMn) * dmem
    assert opnorm_diag(matsub(Fs, Fsn)) <= (normY + normYn) * drec + (normM + normMn) * dmem
record("T16 operator-limit Gram error bounds", 8000)

# T17: vanishing observer-complement residue converges to a faithful finite range.
for _ in range(6000):
    d = rng.randint(2, 8)
    nu = rng.randint(1, d - 1)
    h = rng.randint(1, 6)
    M = [[F(rng.randint(-4, 4)) for _ in range(h)] if i < nu else [F(0)] * h for i in range(d)]
    nidx = rng.randint(2, 50)
    E = [[F(0) for _ in range(h)] for __ in range(d)]
    for i in range(nu, d):
        for j in range(h):
            E[i][j] = F(rng.randint(-2, 2), nidx)
    Mn = matadd(M, E)
    P = diag([F(1) if i < nu else F(0) for i in range(d)])
    assert matmul(P, M) == M
    assert matmul(matsub(eye(d), P), Mn) == E
record("T17 no-hidden-memory convergence fixtures", 6000)

for _ in range(1000):
    d = rng.randint(2, 8)
    nu = rng.randint(1, d - 1)
    P = diag([F(1) if i < nu else F(0) for i in range(d)])
    M = [[F(0)] for __ in range(d)]
    M[-1][0] = F(1)
    residual = matmul(matsub(eye(d), P), M)
    assert frob2(residual) > 0 and matmul(P, M) != M
record("T17 nonvanishing-faithfulness controls", 1000, "PASS_NEGATIVE_CONTROL")

# T18: diagonal singular-value fixtures, exhaustively over coordinate projections.
for _ in range(6000):
    d = rng.randint(1, 7)
    vals = sorted([F(rng.randint(0, 9), rng.randint(1, 5)) for __ in range(d)], reverse=True)
    nu = rng.randint(0, d)
    target = sum((s * s for s in vals[nu:]), F(0))
    best = None
    for inds in itertools.combinations(range(d), nu):
        keep = set(inds)
        tail = sum((vals[i] * vals[i] for i in range(d) if i not in keep), F(0))
        if best is None or tail < best:
            best = tail
    assert best == target
    r = sum(1 for s in vals if s != 0)
    assert (target == 0) == (r <= nu)
record("T18 variational minimal-observer tail", 6000)

# T19: exact inertia, kernel and normalized margin on diagonalized finite-rank models.
choices = [F(0), F(1, 4), F(1), F(6, 5), F(3, 2)]
for _ in range(10000):
    d = rng.randint(2, 9)
    nu = rng.randint(1, min(5, d))
    rvals = [F(rng.randint(1, 5)) for _ in range(d)]
    cvals = [rng.choice(choices) for __ in range(nu)]
    C = [[F(0) for _ in range(d)] for __ in range(nu)]
    for i, s in enumerate(cvals):
        C[i][i] = s
    Dsqrt = diag(rvals)
    R = diag([r * r for r in rvals])
    A = matmul(C, Dsqrt)
    Fop = matsub(R, matmul(transpose(A), A))
    B = matmul(C, transpose(C))
    assert sum(1 for s in cvals if s * s > 1) == sum(1 for i in range(nu) if B[i][i] > 1)
    assert sum(1 for s in cvals if s * s == 1) == sum(1 for i in range(nu) if B[i][i] == 1)
    beta = max((s * s for s in cvals), default=F(0))
    ratios = [Fop[i][i] / R[i][i] for i in range(d)]
    assert min(ratios) == F(1) - beta
record("T19 inertia / kernel / normalized margin", 10000)

# T20: completion error must travel with the finite matrix top.
for _ in range(8000):
    nu = rng.randint(1, 5)
    true = [F(rng.randint(0, 80), 100) for __ in range(nu)]
    perturb = [F(rng.randint(-5, 5), 100) for __ in range(nu)]
    approx = [max(F(0), a + e) for a, e in zip(true, perturb)]
    e = max((abs(a - b) for a, b in zip(true, approx)), default=F(0))
    u = max(approx, default=F(0))
    beta = max(true, default=F(0))
    assert beta <= u + e
    if u + e < 1:
        assert F(1) - beta >= F(1) - (u + e) > 0
record("T20 outward finite promotion", 8000)

for _ in range(1000):
    beta = F(rng.randint(101, 120), 100)
    approx = beta - F(rng.randint(6, 20), 100)
    if approx >= 1:
        approx = F(99, 100)
    e = abs(beta - approx)
    assert approx < 1 and approx + e >= beta > 1
record("T20 fixed-matrix-without-completion-error controls", 1000, "PASS_NEGATIVE_CONTROL")


total = sum(v["trials"] for v in results.values())
report = {
    "status": "PASS_NATIVE_FLOW_COMPLETION_AUDIT",
    "seed": SEED,
    "total_trials_or_exact_cases": total,
    "results": results,
}
print(json.dumps(report, indent=2, sort_keys=True))
