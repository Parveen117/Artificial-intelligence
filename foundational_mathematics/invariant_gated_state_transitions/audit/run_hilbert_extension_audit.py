#!/usr/bin/env python3
from fractions import Fraction as F
import json
import random
from pathlib import Path

SEED = 20260824
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


def eye(n):
    return [[F(int(i == j)) for j in range(n)] for i in range(n)]


def diag(vals):
    n = len(vals)
    return [[vals[i] if i == j else F(0) for j in range(n)] for i in range(n)]


def qform(M, x):
    return dot(x, matvec(M, x))


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


def randvec(n, lo=-4, hi=4):
    return [F(rng.randint(lo, hi)) for _ in range(n)]


def randmat(m, n, lo=-4, hi=4):
    return [[F(rng.randint(lo, hi)) for _ in range(n)] for _ in range(m)]


def givens(n, i, j, a=F(3, 5), b=F(4, 5)):
    Q = eye(n)
    Q[i][i] = a
    Q[i][j] = -b
    Q[j][i] = b
    Q[j][j] = a
    return Q


def signed_perm(n):
    p = list(range(n))
    rng.shuffle(p)
    Q = [[F(0) for _ in range(n)] for __ in range(n)]
    for i, j in enumerate(p):
        Q[i][j] = F(rng.choice([-1, 1]))
    return Q


def orth_rational(n):
    Q = signed_perm(n)
    if n >= 2:
        for _ in range(rng.randint(1, 3)):
            i, j = rng.sample(range(n), 2)
            Q = matmul(givens(n, i, j), Q)
    return Q


def make_C(n, m, positive=True):
    Ql = orth_rational(n)
    Qr = orth_rational(m)
    vals = [F(rng.randint(0, 8), 10) for _ in range(m)]
    if not positive:
        vals[rng.randrange(m)] = F(rng.randint(11, 18), 10)
    D = [[F(0) for _ in range(m)] for __ in range(n)]
    for i, s in enumerate(vals):
        D[i][i] = s
    C = matmul(matmul(Ql, D), Qr)
    beta = max((s * s for s in vals), default=F(0))
    jmax = max(range(m), key=lambda j: vals[j] * vals[j])
    y = [Ql[i][jmax] for i in range(n)]
    return C, beta, y


results = {}


def record(name, count, status="PASS"):
    results[name] = {"trials": count, "status": status}


ROOT = Path(__file__).resolve().parents[1]
paper = ROOT / "paper"
src = (paper / "main.tex").read_text()
for q in sorted((paper / "sections").glob("*.tex")):
    src += "\n" + q.read_text()
for token in (
    "Finite-channel Hilbert compression",
    "Strictly positive source form",
    "Rank-one burden",
    "Positive projection defect",
    "Birman--Schwinger/Schur-complement",
):
    assert token in src

# H1: exact factorization, inverse-form shadow, and positive/negative cases.
for trial in range(12000):
    m = rng.randint(1, 5)
    n = rng.randint(m, m + 5)
    positive = trial % 2 == 0
    C, beta, y = make_C(n, m, positive)
    ds = [F(rng.randint(1, 5)) for _ in range(n)]
    Fm = diag(ds)
    S = diag([d * d for d in ds])
    V = matmul(Fm, C)
    defect = matsub(S, matmul(V, transpose(V)))
    factor = matmul(matmul(Fm, matsub(eye(n), matmul(C, transpose(C)))), Fm)
    assert defect == factor

    Sinv = diag([F(1, d * d) for d in ds])
    B = matmul(matmul(transpose(V), Sinv), V)
    assert B == matmul(transpose(C), C)

    z = [y[i] / ds[i] for i in range(n)]
    if positive:
        for _ in range(2):
            w = randvec(n)
            assert qform(defect, w) >= (F(1) - beta) * qform(S, w)
    else:
        assert qform(defect, z) == F(1) - beta
        assert qform(defect, z) < 0
record("H1 finite-channel compression / inverse-form shadow", 12000)

for _ in range(1000):
    n = rng.randint(2, 8)
    S = diag([F(0)] + [F(rng.randint(1, 5)) for _ in range(n - 1)])
    V = [[F(1)] if i == 0 else [F(0)] for i in range(n)]
    defect = matsub(S, matmul(V, transpose(V)))
    e0 = [F(1)] + [F(0)] * (n - 1)
    assert qform(defect, e0) < 0
record("H1 source-support necessity controls", 1000, "PASS_NEGATIVE_CONTROL")

# H2: target-repair dimension sanity check, retained as a representation-level shadow of T18.
for _ in range(8000):
    a = rng.randint(1, 4)
    r = rng.randint(1, 5)
    t = rng.randint(0, 4)
    n = a + r + t
    A = [[F(int(i == j)) for j in range(n)] for i in range(a)]
    L = [[F(int(a + i == j)) for j in range(n)] for i in range(r)]
    G0 = [row[:] for row in L]
    assert rank(A + G0 + L) == rank(A + G0)
    if r > 1:
        G = randmat(r - 1, n)
        assert rank(A + G + L) > rank(A + G)
record("H2 target-repair dimension shadow", 8000)

# H3: strict reserve and a sharp witness on the top singular channel.
for _ in range(8000):
    m = rng.randint(1, 5)
    n = rng.randint(m, m + 5)
    C, beta, y = make_C(n, m, True)
    ds = [F(rng.randint(1, 5)) for _ in range(n)]
    Fm = diag(ds)
    S = diag([d * d for d in ds])
    V = matmul(Fm, C)
    defect = matsub(S, matmul(V, transpose(V)))
    z = [y[i] / ds[i] for i in range(n)]
    assert qform(defect, z) == (F(1) - beta) * qform(S, z)
    for _ in range(2):
        w = randvec(n)
        assert qform(defect, w) >= (F(1) - beta) * qform(S, w)
record("H3 strict reserve and sharp top-channel witness", 8000)

# H4: projection defect equals a positive Gram difference exactly.
for _ in range(12000):
    n = rng.randint(1, 8)
    m = rng.randint(1, 5)
    p = rng.randint(0, n)
    R = randmat(n, m)
    P = diag([F(1) if i < p else F(0) for i in range(n)])
    ImP = matsub(eye(n), P)
    K = matmul(matmul(transpose(R), ImP), R)
    Gtot = matmul(transpose(R), R)
    Gsrc = matmul(matmul(transpose(R), P), R)
    assert K == matsub(Gtot, Gsrc)
    c = randvec(m)
    w = matvec(ImP, matvec(R, c))
    assert qform(K, c) == dot(w, w) >= 0
record("H4 projection-defect positivity / Gram difference", 12000)


total = sum(v["trials"] for v in results.values())
report = {
    "status": "PASS_HILBERT_FINITE_CHANNEL_EXTENSION_AUDIT",
    "seed": SEED,
    "total_trials_or_exact_cases": total,
    "results": results,
}
print(json.dumps(report, indent=2, sort_keys=True))
