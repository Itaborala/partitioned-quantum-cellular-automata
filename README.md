# PQCA (Partitioned Quantum Cellular Automata)

A quantum cellular automaton iteratively applies some update circuit to some initial state.
A partitioned quantum cellular automaton (PQCA) derives its update circuit by partitioning
a lattice of qubits into cells, and then applying the same circuit to each cell.
The full update circuit is created by composing several such partitioned updates.
There is a review of Quantum Cellular Automata by Terry Farrelly, published in Quantum, and available at [doi:10.22331/q-2020-11-30-368](https://doi.org/10.22331/q-2020-11-30-368).

This python module allows for the easy creation and execution of partitioned quantum cellular automata.
To create an automaton you will need:
 - A starting state (list of 0s and 1s)
 - Update Frames (see `pqca.update_frame`)
 - Optionally, a simulator / quantum computer (see `pqca.backend`)

An Update Frame combines a tessellation with a circuit to be applied
to each cell in that tessellation.
A tessellation just partitions a list of qubits into cells. For example
`pqca.tessellation.one_dimensional(10,2)`
partitions 10 qubits into 5 cells, each of size 2.
The Update Frame would then need to be a circuit on 2 qubits.
For more complicated tessellations you can use, e.g.
`pqca.tessellation.n_dimensional([4,2,4],[2,2,2])`
which partitions 32 qubits as though they were arranged in a lattice
of shape `4 x 2 x 4`, with each cell of size `2 x 2 x 2`.
The Update Frame would then need to be a circuit on 8 qubits.

One can then call `next(automaton)` which will advance the internal state of the automaton and return the new state.

## Installation

Install via `pip` from the command line with the command:
```
pip install pqca
```

## Example

Here is an example that creates two update frames,
both applying a simple CX gate, but with offset tessellations.
```python
# Create circuit
cx_circuit = qiskit.QuantumCircuit(2)
cx_circuit.cx(0, 1)

# Create tessellation
tes = pqca.tessellation.one_dimensional(10, 2)

# Create update frames
update_1 = pqca.UpdateFrame(tes, cx_circuit)
update_2 = pqca.UpdateFrame(tes.shifted_by(1), cx_circuit)


# Create initial state
initial_state = [1]*10

# Create the automaton
# With no backend given, a built-in statevector simulator is used by default.
# See backend.py for more details and instructions on coding your own backend
automaton = pqca.Automaton(initial_state, [update_1, update_2])

# The automaton can be called like any other iterator
# The following line advances the internal state, and returns the new state
next(automaton)
```

## Execution modes

The automaton can be run under different modes by passing a `mode`. A mode
decides what is carried from one step to the next and how the state is prepared
each step. Every mode emits a list of 0s and 1s from `next(...)`.

| Mode | Carried between steps | Behaviour |
| --- | --- | --- |
| `Unitary` (default) | the full statevector | Evolves the statevector directly; the emitted bits are a sample that does not disturb the carried state. |
| `Markovian` | one measured bitstring | Measure-and-restart. Each step collapses to a single result, giving a classical-quantum Markov chain. |
| `Marginal` | per-qubit probabilities | Re-prepares a product state matching the per-qubit statistics each step. Discards phase and correlations. |
| `Legacy` | one measured bitstring | The exact pre-v3 behaviour, kept for reproducing old runs. Uses the old backend. |

```python
# The default mode, shown here explicitly
pqca.Automaton(initial_state, [update_1, update_2], mode=pqca.Unitary())

# Classical-Quantum Markov-chain behaviour
pqca.Automaton(initial_state, [update_1, update_2], mode=pqca.Markovian())

# Product-state approximation, averaged over several shots
pqca.Automaton(initial_state, [update_1, update_2], mode=pqca.Marginal(shots=512))
```

`Unitary` evolves the statevector inside Qiskit and does not use an external
backend. The other modes run circuits, so they accept a backend; if you omit
one, they use the built-in statevector simulator. A custom backend for the new
modes is a function `(circuit, shots) -> list[str]`, returning one bitstring of
`'0'`/`'1'` per shot.

## Running many steps at once

The `Unitary` mode evolves a statevector and so has no equivalent on a circuit
simulator or real hardware: there, each time step must be run as its own circuit.
`BatchedEvolution` does exactly that. It builds the circuit for every requested
step, runs them once through a backend, stores the measurement results, and then
lets you read out a sample per step, separating the cost of simulation from the
act of reading results.

```python
evolution = pqca.BatchedEvolution(initial_state, [update_1, update_2])
evolution.run([0, 1, 2, 3])           # build and simulate steps 0 through 3

for sample in evolution:               # emit one sampled state per step
    print(sample)
```

## Migrating from older versions (pre-3.0)

Version 3.0 reorganises how the automaton runs. The changes are summarised below.

**Reproducing published results.** If you have a notebook or paper that depends
on the old behaviour and you just want it to keep working unchanged, pin the old
release:

```
pip install pqca==2.0.0
```

Everything below is only relevant if you want to move existing code onto v3.

**The default behaviour changed.** Before v3, `pqca.Automaton(state, frames, backend)`
ran measure-and-restart (Markov-chain) dynamics. In v3 the default is `Unitary`,
which behaves differently. To keep the old behaviour, choose the mode explicitly:

```python
# old default behaviour, now requested explicitly
pqca.Automaton(state, frames, mode=pqca.Markovian())

# for bit-for-bit reproduction of pre-v3 runs, including the old backend:
backend = pqca.backend.qiskit()        # requires: pip install pqca[ibm]
pqca.Automaton(state, frames, backend, mode=pqca.Legacy())
```

**The backend is now optional.** Previously you had to supply a backend. Now,
omitting it uses a built-in statevector simulator that ships with the core
package, so `pqca.Automaton(state, frames)` works on its own.

**The backend function signature changed.** A custom backend used to be a
function taking one argument and returning a list of integers:

```python
# old style
def my_backend(circuit):
    return [0, 1, 1, 0]                # one shot, list of ints
```

New modes expect a function taking the circuit and a shot count, and returning
one bitstring per shot:

```python
# new style
def my_backend(circuit, shots):
    return ["0110", "1001"]            # `shots` strings of '0'/'1'
```

If you have an old-style backend you do not want to rewrite, use it with
`Legacy` mode, which still speaks the old contract.

**Reading the current state.** `automaton.state` still returns the most recent
emitted list of 0s and 1s, as before.

**The IBM runtime is now an optional install.** The package no longer requires
`qiskit_ibm_runtime`. Install it with `pip install pqca[ibm]` if you use the
legacy `pqca.backend.qiskit()` backend.

## Documentation

Detailed documentation can be found at [readthedocs.io](https://partitioned-quantum-cellular-automata.readthedocs.io/en/latest/) as well as
in the docstrings of the python files themselves.

## Licensing

The source code is available under the MIT licence and can be found
on [Hector Miller-Bakewell's github](https://github.com/hmillerbakewell/partitioned-quantum-cellular-automata).

## Acknowledgements

This package was created as part of the [QuTune Project](https://iccmr-quantum.github.io/).
