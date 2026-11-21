# TL;DR: Consciousness as Interpretation

Paper: `revised.pdf` in this folder. Record: https://doi.org/10.5281/zenodo.24358525 (always points to the latest version).

## What it is

A paper on consciousness. It proposes a coupling model in which conscious experience forms where the body meets a timeless relational field, and it applies the model to known medical cases.

For physicists it may be of interest as a use case: the mapping it describes runs from quantum physics onto gravitational physics, in one locally bounded special case. It is not a theory of quantum gravity and does not claim to be one.

The two usual objections are addressed. No homunculus is needed, because the observer is formed in the mapping event and has no work left to do. Warm, wet coherence is not assumed against the evidence; it rests on measured results, including spin echo inside living cells with a coherence time near 1 µs (Ishiwata et al. 2026), superradiance in tubulin assemblies (Babcock et al. 2024), energy migration in microtubules (Kalra et al. 2023), and the sources in Appendix B. A claim graph with an objection index is in [CLAIMS.md](CLAIMS.md).

## The model in one paragraph

Three parts meet. The local client is the organism: its hardware, its life history (`B_i`) and its present state. The server is a timeless relational field. It holds relations but has no viewpoint of its own. The mapping event `K_i` connects the two. It compares the inputs, assigns source and perspective, and forms the branches that are available to this biological system. One branch becomes real through objective reduction in the microtubule carrier, and the result is written back into the client's history. The lived image `Psi_i` is formed in that meeting. Neither the body nor the field is conscious alone.

Core equation (Section "The Complete Interpreter Model"):

    Psi_i = K_i( D_local, D_server, G_i | u_i )
    integral_0^tau E_G ds = hbar,   for constant E_G:  tau = hbar / E_G

## What it does not borrow

The gravitational self-energy `E_G` is calculated directly from the atomic coordinates of the tubulin dimer, without calibrating it to any collapse time. It grows almost linearly with the number of recruited dimers, so no hidden N^2 amplification is needed. For event intervals of 25 to 500 ms the carrier population lies between about 10^9 and 10^12 dimers.

## From the timeless state to ordinary spacetime

The server side starts from the Wheeler-DeWitt constraint `H|Phi> = 0`, which has no time parameter. Relations are read from it as correlation strengths at a local address, and nothing on the server evolves.

The link to the spacetime of general relativity runs through causal dynamical triangulations. Only an effective, coarse-grained Lorentzian metric is taken from the CDT ensemble. On that local patch the client's worldline gives its proper time `u_i` and a spatial rest slice. On this slice the Green kernel reduces to the Newtonian `1/|x-y|` in the local flat limit, and Penrose's gravitational self-energy `E_G` is evaluated there. Twistor incidence is used only as a local address in the flat tangent space, not as a global construction.

In short, the timeless relational state is coupled to ordinary, locally Einsteinian spacetime at one place: the mass-density difference of the carrier branches on the client's own rest slice.

## Appendices in brief

- **A. Notation and Definitions:** all symbols in one table.
- **B. Neurodynamic and Biological Implementation:** the measured carrier constraints with their sources (Froehlich condensation, warm biological coherence, superradiance, anaesthetic effects on microtubules, epothilone B), plus a Wilson-Cowan population field and an adaptive integrate-and-fire neuron that set the local trigger.
- **C. Quantum-Gravitational Coupling and Derivations:** the chain from the Wheeler-DeWitt state through CDT and the local time vector to the twistor address. It also covers the weighting of relations, which is bounded by monotonicity constraints only, and a consistency lemma. That lemma shows the weighting is a completely positive instrument: outcome probabilities stay ordinary Born probabilities and no signalling between clients is possible. A Bohmian quantum potential carries form before reduction only. Froehlich-type recruitment sets which carrier domains join. The geometric `E_G` is computed from the 1JFF tubulin structure, and the deviation from linear scaling stays below 7.6e-15 up to about 3.4 million dimers. Reduction depends on accumulated recruitment, not on an instantaneous count.
- **D. Model Tests and Numerical Results:** a finite associative load of about 0.14 patterns per unit (Hopfield limit), a relational-convergence benchmark built from published recall data with a preregistered protocol, and the sensitivity of the adaptive trigger.
- **E. Mapping Disruption and Resynchronisation:** after an interruption, the unresolved gap `G_i` shrinks cycle by cycle until it is empty.

## Questions the paper already addresses

- Homunculus: no inner viewer is needed. The observer is part of what the meeting forms, so no homunculus is needed to watch it.
- Coherence in warm, wet tissue: recent measurements show it is not ruled out (Babcock et al. 2024, Kalra et al. 2023). The paper does not treat this as an open gap.
- "If Orch OR fails, everything fails": no. The model is modular. What carries it is the meeting of a living history and a shared relational field in one mapping. The carrier (microtubules), the route to local geometry (CDT), the form layer (Bohmian potential), the reduction (Orch OR) and the neuron model (AdEx) are the best parts known today, each marked in the text with the property a substitute must keep. The ratio and epothilone tests check these parts. The model as a whole fails only if relational structure before recall does not predict convergence, or if everything met for the first time can be explained by what was already learned.

## Tests with existing methods

- Two independently characterised carrier states: the ratio of their event intervals should follow the inverse ratio of their gravitational self-energies.
- Anaesthesia: microtubule stabilisation with epothilone B already delays loss of responsiveness. The model predicts that the size of the delay follows the measured change in the carrier.
- Heat: speed and integrity of a response should move in opposite directions while early registration stays intact.
- Memory: relational structure measured before recall should predict how strongly and how quickly a memory converges (preregistered protocol in the paper).
- Clinical dissociations: writing, filling, anchoring and recovery can fail one at a time. For a patient who does not respond, the question becomes where in the cycle the mapping is disturbed.

## Open by design

The exact form of the weighting function `W_i` is not yet fixed, only the direction of its dependencies. It is not free, though. Appendix C bounds it between 0 and 1 (weighting can only damp), makes it depend on local geometric invariants rather than coordinates, fixes four signs (more biographical affinity and pattern overlap raise the weight; more proper-time and spatial distance lower it), uses one shared rule across all applications, and excludes spacelike settings (no signalling). Its inputs are client quantities, not the carrier's quantum state, so the weighting stays a linear instrument. The relational field is not observed directly. The tests, not a look at the server, decide whether the model holds.

## How to read it

The chapters are written to guide a non-specialist reader step by step. Derivations, simulations and data are in the appendices and in `simulations/` and `data/`.
