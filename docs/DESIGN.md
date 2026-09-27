This is an initial, exact computational framework for rank-4, 11-element GF(5) excluded minors. It has been validated on small examples. **It is not yet an exhaustive search of the target class.**

The eventual output should contain one representative of every matroid isomorphism class, a GF(5) nonrepresentability certificate for each representative, representations of all its immediate minors, and a separate argument/certificate that candidate generation was exhaustive.

For a candidate M on E, the decision condition is

\[
 M\text{ is not GF(5)-representable},\qquad
 M\setminus e,\ M/e\text{ are GF(5)-representable for every }e\in E.
\]

Checking these 22 immediate minors suffices because every proper minor is a minor of an immediate one, and representability is minor closed. A timeout leaves the result unresolved. Contractions can have loops or parallel elements, and the implementation handles them directly.

**Candidate coverage.** For any target excluded minor M and element e, the deletion N=M\e is a simple, GF(5)-representable rank-4 matroid on ten elements: an excluded minor of this size has no loops, coloops, parallel pairs, or series pairs. A logically complete baseline would therefore:

1. Generate every simple represented rank-4 parent N of size ten, up to abstract matroid isomorphism, with a proof of coverage.
2. Enumerate every abstract rank-preserving single-element extension of each N.
3. Apply the exclusion test above and deduplicate accepted matroids by isomorphism.

The new code implements step 2 for one supplied parent and the recognition part of step 3. It provides an exact Sage isomorphism key, but no global catalogue merger or exhaustive implementation of step 1. Deletions of 3-connected matroids need not be 3-connected; limiting parents to 3-connected ones requires an additional theorem and coverage argument. No paving or sparse-paving assumption is used.

A simple rank-4 GF(5) matroid is a spanning restriction of PG(3,5), which has (5^4-1)/4=156 points. Directly listing all 10-subsets is an expensive reference model. Even after fixing a basis to the four coordinate points, there are C(152,6) choices before further equivalences. There is no evidence from the smoke tests that this whole baseline is practical. While growing represented parents, retaining only one representation per abstract matroid can lose later extensions. Either retain all inequivalent representations or justify the reduction with stabilizer theory. Deduplicating *completed parents before taking all abstract extensions* is safe.

**The extension SAT encoding.** There is one Boolean b_S for each r-subset S of the n-element ground set. A fixed deletion parent determines all variables not containing the new element. Include, for all ordered r-subsets A,B and every x in A\B,

\[
 \neg b_A\lor\neg b_B\lor
 \bigvee_{y\in B\setminus A} b_{A-x+y}.
\]

The valid parent's fixed bases ensure nonemptiness. These clauses are exactly the basis-exchange axiom, so every model defines a matroid and every extension yields a model. Optional simplicity requires each singleton and pair to lie in some basis; cosimplicity applies the same condition to complements of bases. Both conditions are necessary for the target excluded minors. The encoding has 330 basis variables at (r,n)=(4,11), of which 210 are fixed by the parent and 120 are free. These are **not** bounds on the number of candidates.

Models are blocked using the free basis variables. Journals store complete labelled basis families. Resuming verifies the parent, filters and source-code digest, validates saved records, and blocks them before continuing. `EXHAUSTED` means only the constrained extension family of that labelled parent was exhausted. Hitting the model limit or time limit is recorded explicitly. No enumeration DRAT certificate is currently produced.

**The representation SAT encoding.** Fix a basis B, transform any representation into [I_r|A], and recover the zero pattern using

\[
 A_{ij}\ne0\quad\Longleftrightarrow\quad B-b_i+e_j\text{ is a basis}.
\]

The bipartite graph of nonzero entries has row and nonbasis-column vertices. Row and column scalings can set the entries of any spanning forest to 1: root each component and successively choose the scale at each new vertex. Scaling the basis columns compensates for row scalings and restores I_r. This fixes no cross-ratio and is valid also for disconnected supports. Each remaining nonzero entry ranges over {1,2,3,4}.

For every r-subset S, enforce the nonzero/zero status of the complementary square minor of A according as S is a basis/nonbasis. These minors and the corresponding full matrix determinants differ only by sign. Constants, one-hot field values, and exact addition/multiplication tables encode arithmetic modulo 5. A cached Laplace expansion compiles determinants. All maximal minors are constrained, not just selected circuits. Thus a representation yields a satisfying assignment after normalization, and a satisfying assignment yields exactly the specified labelled matroid.

Each SAT witness is checked by a separate integer Gaussian-elimination routine on every maximal minor. The first validation also checks saved witnesses using Sage finite-field matrices. UNSAT runs can save a DIMACS instance, encoding map, original matroid, and Glucose DRAT output. `proof_checked` remains false: no independent DRAT checker was installed or invoked. Re-solving small CNFs with MiniSat is a regression check, not a substitute for a proof checker.

**Isomorphism and storage.** The JSON schema `gf5-bases-v1` records n, rank, and all bases, with labels 0,...,n-1. Every imported record is checked for basis exchange. Immediate minors remove an element and renumber the remaining labels in increasing order; result records include their parent-label order. A labelled SHA-256 is a storage identifier, never an isomorphism test. The optional Sage bridge canonically labels the bipartite incidence graph of elements versus the smaller of the basis/nonbasis families, preserving the two vertex colors. Its full key includes size, rank, and family choice. Pin the Sage/backend version when comparing keys across runs. Rank-4 and rank-7 duals are not identified with each other.

The next phase should have explicit acceptance criteria:

| Work | Required evidence before scaling |
| --- | --- |
| Convert the existing smaller catalogue to portable JSON | Source digest, counts by rank/size, validity checks, exact isomorphism checks; no automatic execution of downloaded Sage code |
| Reproduce smaller classifications | At least the published rank-4 size-7/8 counts initially, then size-9/10 counts before any size-11 completeness claim |
| Choose parent generation strategy | A written coverage argument; preservation of inequivalent representations; comparison with established Sage/MACEK methods |
| Benchmark representative ten-element parents | Candidate rates, recognition cost, memory, fraction UNKNOWN, and pruning effectiveness |
| Add accelerations | Compare with the baseline on exhaustive small families before using symmetry, stabilizers, splicing, or forbidden-minor cuts |
| Make results certifiable | Independently check all final UNSAT proofs and minor witnesses; account for every shard and deduplicate exactly |

Splicing over nine-element common deletions is a promising next experiment because two specified deletion parents determine more of the extension. A second option is SAT with representation witnesses for every immediate minor and an outer nonrepresentability check. Simultaneously asking for existence of a matroid and absence of *all* its representations has a quantifier alternation; simply negating an existential matrix formula in ordinary SAT is not a sound shortcut. The initial implementation keeps generation and recognition separate.

The comparative literature and the hypotheses behind the more sophisticated reductions are in [LITERATURE.md](LITERATURE.md). No structural acceleration or large cluster campaign is claimed to have been implemented yet.
