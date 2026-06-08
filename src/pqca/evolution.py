import random
from typing import List, Callable, Iterable

from qiskit import QuantumCircuit

from .update_frame import UpdateFrame
from .modes import _bits, _pattern_preparation_circuit
from .backend import statevector_backend
import copy


class BatchedEvolutionPQCA:
    """Discrete-time evolution circuits for a PQCA, evauluated in batches for each time step."""

    def __init__(self, initial_state: List[int], frames: List[UpdateFrame], backend: Callable = None, *, shots: int = 128):

        self.initial_state = initial_state
        self.frames = frames
        self.backend = backend if backend is not None else statevector_backend
        self.shots = shots

        self._step_circuit = QuantumCircuit(len(initial_state))

        for frame in frames:
            for instruction, qargs, cargs in frame.full_circuit_instructions:
                self._step_circuit.append(instruction, qargs, cargs)


        self._memory: dict[int, List[str]] | None = None
        self._order: List[int] = []
        self._iter = None


        def build_circuits(self, time_steps: Iterable[int], measure: bool = True) -> List[QuantumCircuit]:


        order = list(time_steps)
        if any(t < 0 for t in order):
            raise ValueError("Time steps must be non-negative integers.")

        sorted_unique = sorted(set(order))

        cache = {}

        running = copy.deepcopy(_pattern_preparation_circuit(self.initial_state))

        previous_t = 0

        for t in sorted_unique:
            for i in range(t - previous_t):
                running.compose(self._step_circuit, inplace=True)

            snapshot = copy.deepcopy(running)
            if measure:
                snapshot.measure_all()
            cache[t] = snapshot
            previous_t = t

        return [cache[t] for t in order]



    def run(self, time_steps: Iterable[int]):

        self._order = list(time_steps)
        circuits = self.build_circuits(self._order, measure=True)

        self._memory = { t: self.backend(circuit, shots=self.shots) for t, circuit in zip(self._order, circuits) }
        self._iter = iter(self._order)

        return self

    def __iter__(self):

        return self

    def __next__(self) -> List[int]:
        """Emits one sampled bitstring per stored step."""

        if self._iter is None:
            raise RuntimeError("Must call run() before iterating.")

        t = next(self._iter)
        return _bits(random.choice(self._memory[t]))

            


