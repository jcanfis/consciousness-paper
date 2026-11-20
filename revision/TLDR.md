# TL;DR: Consciousness as Interpretation

Paper: `revised.pdf` in this folder. Record: https://doi.org/10.5281/zenodo.24358525 (always points to the latest version).

## What it is

A paper on consciousness. It proposes a coupling model in which conscious experience forms where the body meets a timeless relational field, and it applies the model to known medical cases.

For physicists it may be of interest as a use case: the mapping it describes runs from quantum physics onto gravitational physics, in one locally bounded special case. It is not a theory of quantum gravity and does not claim to be one.

## The model in one paragraph

Three parts meet. The local client is the organism: its hardware, its life history (`B_i`) and its present state. The server is a timeless relational field. It holds relations but has no viewpoint of its own. The mapping event `K_i` connects the two. It compares the inputs, assigns source and perspective, and forms the branches that are available to this biological system. One branch becomes real through objective reduction in the microtubule carrier, and the result is written back into the client's history. The lived image `Psi_i` is formed in that meeting. Neither the body nor the field is conscious alone.

Core equation (Section "The Complete Interpreter Model"):

    Psi_i = K_i( D_local, D_server, G_i | u_i )
    integral_0^tau E_G ds = hbar,   for constant E_G:  tau = hbar / E_G

## What it does not borrow

The gravitational self-energy `E_G` is calculated directly from the atomic coordinates of the tubulin dimer, without calibrating it to any collapse time. It grows almost linearly with the number of recruited dimers, so no hidden N^2 amplification is needed. For event intervals of 25 to 500 ms the carrier population lies between about 10^9 and 10^12 dimers.

## Questions the paper already addresses

- Homunculus: no inner viewer is needed. The observer is part of what the meeting forms, so no homunculus is needed to watch it.
- Coherence in warm, wet tissue: recent measurements show it is not ruled out (Babcock et al. 2024, Kalra et al. 2023). The paper does not treat this as an open gap.

## Tests with existing methods

- Two independently characterised carrier states: the ratio of their event intervals should follow the inverse ratio of their gravitational self-energies.
- Anaesthesia: microtubule stabilisation with epothilone B already delays loss of responsiveness. The model predicts that the size of the delay follows the measured change in the carrier.
- Heat: speed and integrity of a response should move in opposite directions while early registration stays intact.
- Memory: relational structure measured before recall should predict how strongly and how quickly a memory converges (preregistered protocol in the paper).
- Clinical dissociations: writing, filling, anchoring and recovery can fail one at a time. For a patient who does not respond, the question becomes where in the cycle the mapping is disturbed.

## Open by design

The exact form of the weighting function `W_i` is not yet fixed, only the direction of its dependencies. The relational field is not observed directly. The tests, not a look at the server, decide whether the model holds.

## How to read it

The chapters are written to guide a non-specialist reader step by step. Derivations, simulations and data are in the appendices and in `simulations/` and `data/`.
