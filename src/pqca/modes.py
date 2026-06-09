from abc import ABC, abstractmethod
import math
import random
from typing import List, Callable

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


# Builtin backend for pqca>=3.0.0
Backend = Callable[[QuantumCircuit, int], List[str]]
# Legacy backend for pqca<=2.0.0
LegacyBackend = Callable[[QuantumCircuit], List[int]]


def _bits(shot: str) -> List[int]:
    """reversing bit order to match the little-endian convention used by qiskit"""
    return [int(bit) for bit in shot[::-1]]


def _pattern_preparation_circuit(pattern: List[int]) -> QuantumCircuit:
    """ Create a circuit that encodes the given classical state.

    Args:
        pattern (List[int]): A list of 0s and 1s.

    Returns:
        QuantumCircuit: A circuit that encodes the given classical bits as the tensor product of 0 and 1 states.
    """
    circuit = QuantumCircuit(len(pattern))
    for (qubit, boolean_value) in list(enumerate(pattern)):
        if boolean_value:
            circuit.x(qubit)

    return circuit


def _real_product_state_circuit(marginals: List[float]) -> QuantumCircuit:
    """ Create a circuit that prepares a product state with the given marginal probabilities of each qubit.

    Args:
        marginals (List[float]): A list of probabilities for each qubit being in the |1> state.

    Returns:
        QuantumCircuit: A circuit that prepares the desired product state.
    """
    circuit = QuantumCircuit(len(marginals))
    for (qubit, p1) in list(enumerate(marginals)):
        if marginal > 0:
            theta = 2 * math.acos(math.sqrt(1 - marginal))
            circuit.ry(theta, qubit)

    return circuit


class PQCAMode(ABC):
    """ Strategy selector for running PQCA routines """

    legacy_backend: bool = False

    @abstractmethod
    def init_carrier(self, initial_state: List[int]):
        """ Sets up the initial state of the PQCA. """

    @abstractmethod
    def advance(self, carrier, update_circuit: QuantumCircuit, backend):
        """ Advances one iteration of the PQCA Mode's routine."""



class LegacyPQCA(PQCAMode):
    """ Legacy code for pqca<=2.0.0 functionality. Similar to the MarkovianPQCAMode in pqca>=3.0.0 """

    legacy_backend: bool = True

    def init_carrier(self, initial_state: List[int]):
        return initial_state

    def advance(self, carrier, update_circuit, backend):
        circuit = _pattern_preparation_circuit(carrier).compose(update_circuit)
        bits = backend(circuit)
        return list(bits), list(bits)


class MarkovianPQCA(PQCAMode):
    """ An execution mode for running Measurement Quantum Cellular Automata routines.
    Fully destructive measurement-and-reset after each iteration, carrying the latest measured bitstring ad feedback.
    bitstrinc gis both the emitted output andthe entire state carried forward. 
    Reduces the multi-step dynamics to a quantum-evaluated Markov chain.
    Performs the same function as the LegacyPQCAMode for pqca>=3.0.0, but with a different backend interface.
    """

    def init_carrier(self, initial_state):
        return initial_state


    def advance(self, carrier, update_circuit, backend):
        circuit = _pattern_preparation_circuit(carrier).compose(update_circuit)
        bits = _bits(backend(circuit, shots=1)[0])
        return bits, bits

class MarginalPQCA(PQCAMode):
    """ An intermediary execution mode for PQCA routines.
    Semi-destructive. Carries per-qubit marginal probabilities (P(q_i = |1>), but destroys correlations, entanglement, and phases between qubits.
    emits one sampled bistring from shot memory, and carries real-valued product states forward to the next iteration based on current marginals.
    """

    def __init__(self, shots: int = 1024):
        self.shots = shots

    def init_carrier(self, initial_state):
        return [float(bit) for bit in initial_state]

    def advance(self, carrier, update_circuit, backend):
        circuit = _real_product_state_circuit(carrier).compose(update_circuit)
        memory = backend(circuit, self.shots)
        marginals = [
            sum(_bits(shot)[i] for shot in memory) / self.shots
            for i in range(self.shots)
        ]
        emitted = _bits(random.choice(memory))
        return marginals, emitted


class UnitaryPQCA(PQCAMode):
    """ Standard Partitioned Unitary Quantum Cellular Automata.
    Non-destructive, fully coherent unitary discrete-time evolution of the initial state.
    Carries the full statevector and evolves it directly (U^n |psi_t0>).
    Emitted is sampled independently from the distribution defined by the statevector, and hence does not collapse the quantum state. 
    This is pure statevector simulation, so the ``backend`` argument is ignored, since this is not designed for execution on actual quantum hardware.
    Refer to the BatchedEvolutionPQCAMode for a version of this mode that is designed for execution on quantum hardware and custom backends.
    """

    def init_carrier(self, initial_state):
        label = "".join(str(int(bit)) for bit in reversed(initial_state))
        return Statevector.from_label(label)

    def advance(self, carrier, update_circuit, backend):
        evolved = carrier.evolve(update_circuit)
        emitted = _bits(evolved.sample_memory(1)[0])
        return evolved, emitted

