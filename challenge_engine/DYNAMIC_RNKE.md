# Dynamic RNKE: Morphism-First Recognition Before Commitment

## Status

`dynamic-rnke-transition-v1` is the current experimental transition layer for RNKE.

Its primitive object is not a timestamped pair of database states. The primitive is an admissible transition, or morphism,

```text
x --a--> y
```

A notation such as

```text
S_t -> S_{t+1}
```

is a useful connector presentation of that morphism. The labels `t`, `t+1`, an epoch, block height, iteration number, JSON encoding, vector basis, or database version are not automatically part of the native object.

This distinction follows the clock-free Recognition-Seam / morphic architecture: evolution is an admissible arrow first; clocks and representations are secondary ways of measuring or displaying that arrow.

## 1. Native recognition object

For a typed transition `a:x->y`, the conceptual Recognition-Seam object compares:

```text
recognize after native transport
versus
transport the recognized object
plus the lawful ledger
```

Schematically,

```text
seam(a;u)
  = Rec_y(Tran_a u)
  - RTran_a(Rec_x u)
  - Ledger_a(u).
```

The transition is recognition-closed when the declared seam/residual vanishes in the comparison sector.

RNKE expresses the same architecture operationally:

```text
candidate morphism
+ evidence
+ dependencies
+ frozen recognition/authority rules
+ current lineage state
        |
        v
ADMIT | REJECT | INCOMPLETE | INVALID
```

An `ADMIT` prepares a transition. It does not by itself perform an external side effect.

## 2. Clock independence

A clock may assign a duration, scale, iteration number, entropy coordinate, block height, or other label to a transition. It is not required to define the transition.

If a clock `tau` is lawful and nondegenerate, one may form a normalized rate such as

```text
seam_rate = seam / tau(a).
```

Changing clocks may change that rate. It does not change whether the underlying integrated seam is zero.

Therefore:

```text
native transition / integrated residue   clock-independent
normalized rate                          clock-dependent presentation
```

A flat or singular clock does not prove that the transition is closed. It means that the selected rate coordinate cannot resolve the transition. Another presentation, an integrated residue, or retained memory may still detect it.

This corrects an older morphic-calculus overstatement in which a flat clock was described as making all derivatives vanish. In the hardened RSC interpretation, clock failure is presentation failure, not automatic native closure.

### Important agent distinction

A field that resembles time is not automatically a removable clock coordinate.

For example, if a grant is valid only for committed epochs `10..20`, then the epoch participates in the authorization predicate. Changing it changes the semantic state of the transition. It is not a harmless reparameterization.

## 3. Base / representation independence

Base independence does not mean "ignore the representation." It means that a proved change of presentation carries the recognition obstruction covariantly.

Conceptually, if `U_x` and `U_y` re-present native states and `V_x`, `V_y` re-present recognized states, a lawful covariance theorem has the form

```text
seam'(a; U_x u) = V_y seam(a;u).
```

Consequences:

```text
seam = 0             -> closure is presentation invariant
seam != 0            -> nonclosure cannot be erased by a lawful invertible re-presentation
V_y is isometric     -> residue norm is invariant
```

This is the precise sense in which RNKE can become base-independent.

### What canonical JSON does and does not prove

The current agent connector canonicalizes JSON before hashing. This proves deterministic serialization inside that connector representation.

It does **not** prove that two different strings, paths, aliases, URLs, account identifiers, coordinate systems, or tool encodings have the same native meaning.

Cross-presentation equivalence requires an adapter that declares and verifies the covariance / faithfulness relation. Until such an adapter closes, RNKE remains deliberately representation-bound at that boundary.

## 4. Factorwise closure, not endpoint cancellation

For composable transitions, Recognition-Seam calculus carries a cocycle-style composition law. The crucial operational lesson is:

```text
factorwise closure -> composite closure
```

but the converse is false in general. Two nonzero residues can cancel at an endpoint.

Therefore Dynamic RNKE does not accept endpoint success as a substitute for the closure of every mandatory factor.

This directly repairs the first Proof-Before-Action challenger break. The old implementation could produce:

```text
local action gate     ADMIT
global RNKE result    FAILED
action_executable     true
```

The morphism-first rule is now:

```text
EXECUTION PREPARATION
    iff local/domain recognition closes
    AND every mandatory global factor closes.
```

No local `ADMIT` may cancel or outrank an unresolved global residue.

## 5. Atomic realization

After recognition, the connector still has to realize the admitted morphism in its concrete state representation.

For the current reference connector:

```text
source representation S
        |
        | RNKE-recognized morphism a
        v
target representation S'
```

RNKE prepares a certificate binding:

```text
frozen Genesis hash
payload/action hash
source-state representation hash
target-state representation hash
recognition result
validator manifest
transition certificate hash
```

The connector then performs an atomic compare-and-swap:

```text
commit S -> S'
iff current_hash == certified_source_hash.
```

Only after the state commit succeeds may a deployment release the corresponding external side effect.

This CAS is not the native definition of the morphism. It is one faithful realization strategy for a mutable software connector.

## 6. Replay as morphism/state conflict

For Proof Before Action, an admitted action consumes its request nonce in the target state.

```text
S  : nonce unused
 a : authorized action
S' : nonce used
```

Two copies of the same prepared certificate may both have been recognized against `S`, but only one can atomically realize `S -> S'`. After the first commit, the second certificate is stale because its certified source representation is no longer current.

The reference test therefore requires 64 concurrent copies of one prepared transition to produce exactly:

```text
1  COMMITTED
63 STALE_STATE
```

This turns replay protection from a later bookkeeping check into part of the state-transition realization.

## 7. Relationship to RNKE special cases

### Mathematics

```text
unadmitted proof state --licensed proof step--> enlarged proof state
```

A theorem is a terminal recognition state reached only through lawful factorwise transitions. A static proof checker is therefore a calm special case of morphic RNKE.

### AI agent

```text
current authority/world state --proposed tool action--> next committed state
```

The model proposes the arrow. It does not create the authority for the arrow.

### Proof of Work

```text
committed chain state --work-bearing candidate--> next chain state
```

Hash/work validation is one obligation inside recognition of the transition, not the definition of RNKE itself.

## 8. Invariants and presentation-dependent quantities

Candidate native / covariant invariants include:

```text
recognition closure versus nonclosure
typed residual / seam class
target-blind quotient dimension and minimum repair rank
ledger curvature / holonomy when declared
native sign or other target property after a faithful adapter
```

Presentation-dependent quantities can include:

```text
timestamps and clock rates
iteration indices
coordinate components
basis labels
Hilbert representing spectra under different metrics
JSON hashes and database version IDs
```

A presentation-dependent quantity may still be essential operational evidence. It simply must not be mislabeled as a native invariant.

## 9. Current implementation boundary

The current code proves a narrower software statement:

- no external clock is required by the transition certificate;
- mutable committed state is evaluation lineage rather than a frozen Genesis rule;
- local `ADMIT` cannot override failed global RNKE recognition;
- successful agent recognition prepares a nonce-consuming target state;
- the reference connector uses exact evaluated-certificate binding plus atomic CAS;
- duplicate/concurrent realization of the same source-state certificate commits at most once;
- canonical JSON is explicitly treated as deterministic serialization, not universal base independence.

The code does **not** yet provide a universal presentation-covariance adapter. Such an adapter must define the relevant equivalence relation and prove that recognition, transport, ledger and target semantics are preserved.

## 10. Compact definition

The resulting architecture can be summarized as:

```text
RNKE verifies admissible morphisms before commitment.

Clocks measure morphisms.
Representations display morphisms.
Ledgers retain what the display can forget.
Recognition decides whether the morphism may commit.
```

Or formally:

```text
x --a--> y

ADMIT(a)
iff
all declared recognition / evidence / authority / lineage residues close.
```

The state notation `S_t -> S_{t+1}` remains useful, but it is now downstream of the more general clock-free object `a:x->y`.
