# Where the pipeline is worse than plain prompting

Comparing NEF 2.0 (`results/final_clean/`) against the no-method 6-shot baseline
(`baseline_luna/`) — identical model (GPT-5.6 Luna), identical benchmark, identical
scorer — the method improves **16 of 19 domains** and regresses on three:

| Domain | Baseline | NEF 2.0 | Δ | Cause | Action |
|---|---|---|---|---|---|
| `10_comicscharacter` | 0.6343 | 0.4000 | **−0.234** | benchmark annotation artifact | **will not fix** (§1) |
| `8_celestialbody` | 0.8352 | 0.7233 | **−0.112** | literal formatting bug | fix (§2) |
| `9_astronaut` | 0.7790 | 0.7377 | −0.041 | same class as §2, smaller | fix follows from §2 |

Combined these cost ≈0.020 macro. Section 2 is recoverable; section 1 is not, by choice.

---

## 1. comicscharacter — the benchmark wants URIs that do not exist

### Evidence

```
SENT:  Auron was created by Karl Kesel and Marv Wolfman...
GOLD:  Auron_(comicsCharacter) | creator | Karl_Kesel
BASE:  Auron_(comicsCharacter) | creator | Karl_Kesel      ✓ f1 = 1.00
OURS:  Auron_(comics)          | creator | Karl_Kesel      ✗ f1 = 0.00
```

20 of 36 sentences in this domain lose more than 0.15 F1 to the baseline, almost
all through this single mechanism.

### Mechanism

`Auron_(comicsCharacter)` **is not a DBpedia resource.** The suffix is an
annotation convention invented by the benchmark. The real entity is
`Auron_(comics)`, which is what our surface-form index correctly returns.

The no-method baseline scores *because* it does no entity linking: it copies the
`_(comicsCharacter)` pattern from its in-context examples and emits a string that
happens to match gold. Our pipeline resolves to the entity that actually exists
and is marked wrong.

The suffix cannot be recovered by lookup either — the four suffixed subjects in
the test gold (`Arion`, `Auron`, `Balder`, `Bolt`) appear **nowhere in the train
gold**, so only the *pattern* is learnable, not the mappings.

### Decision: not fixed

Matching this would require deliberately emitting identifiers that do not resolve
in DBpedia. That contradicts the design principle the whole system is built on —
every emitted triple is either verified against the knowledge base or explicitly
tagged as unverified, and in both cases the URIs are real.

We would gain ≈0.012 macro and lose the property that makes the output usable
downstream. **The benchmark score is a proxy; producing valid triples is the
goal.** We report the regression rather than engineer around it.

*(This also bounds what any system can score here: a method that links entities
correctly is penalised on this domain by construction. NEF 1.0 scores 0.519 —
above ours, below the naive baseline — which is consistent with partial linking.)*

---

## 2. celestialbody — two literal-formatting bugs

### Evidence

```
GOLD:  1147_Stavropolis | periapsis     | 260855000000.0
OURS:  1147_Stavropolis | periapsis     | 260855000000          ← trailing .0 stripped

GOLD:  1147_Stavropolis | orbitalPeriod | 1249.6
OURS:  1147_Stavropolis | orbitalPeriod | 1249.6 (days)         ← unit added

GOLD:  1147_Stavropolis | apoapsis      | 418476000000.0
OURS:  1147_Stavropolis | apoapsis      | 418476000000.0 (kilometres)
```

31 of 72 sentences lose more than 0.15 F1, entirely on numeric formatting. The
entity linking and predicate selection are correct in every case.

### Mechanism

Two independent defects:

**(a) `.0` truncation.** Gold preserves a trailing `.0` on float-valued
properties. Our literal normaliser strips it.

**(b) Parenthetical units applied too broadly.** The Week-9 fix added unit
preservation after observing gold keep `6603633000.0 (kilometres)`. That
convention is **not uniform** — it varies per predicate, and our rule applies it
where gold omits it.

### The convention is per-predicate and noisy

Counts from the train split (`8_celestialbody`):

| Predicate | bare | with unit | keeps `.0` | drops `.0` |
|---|---|---|---|---|
| `periapsis` | 32 | 15 | 32 | 15 |
| `apoapsis` | 11 | 37 | 11 | 37 |
| `orbitalPeriod` | 28 | 13 | 20 | 21 |
| `mass` | 0 | 13 | 0 | 13 |
| `density` | 0 | 1 | 0 | 1 |

`periapsis` is 68% bare, `apoapsis` is 77% unit-bearing — opposite conventions on
adjacent properties of the same class. `orbitalPeriod` is near a coin flip on the
`.0` question, so some of this domain is irreducible noise in the annotations.

### Fix

Extend the existing train-learned convention machinery (the same mechanism behind
per-domain quoting and date styles) with a **per-(domain, predicate) unit and
decimal convention**, learned by majority from train with the same low threshold
used for quoting. Expected recovery: most of the 0.112, i.e. ≈+0.006 macro, with
`9_astronaut` improving by the same mechanism.

This is a legitimate fix: it changes only *formatting of a correct value* to match
the documented convention of the target dataset — no invented identifiers.

---

## Method note

Both findings come from an offline diff of saved per-sentence outputs — no
inference, no API cost. The comparison is only possible because the no-method
baseline was run under the identical harness; running it turned out to be
diagnostically useful well beyond its original purpose of controlling for the
base model.
