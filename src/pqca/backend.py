"""Expose ways of evaluating circuits."""

from typing import List, Callable
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from qiskit_ibm_runtime import SamplerV2 as Sampler, QiskitRuntimeService, IBMBackend
from qiskit_ibm_runtime.fake_provider import FakeFez
from . import exceptions

def statevector_backend(circuit: QuantumCircuit, shots: int) -> List[str]:
    """Basic builtin backend adapter for pqca>=3.0.0, sampling from the statevector directly.

    Custom backends can be used by implementing a function with the same signature and passing it to the Automaton constructor. 
    Please refer to the documentation for more details and instructions on how to implement custom backends.
    """
    bare_circuit = circuit.remove_final_measurements(inplace=False) or circuit
    return Statevector.from_instruction(bare_circuit).sample_memory(shots)

def qiskit(backend: IBMBackend = FakeFez()) -> Callable[[QuantumCircuit], List[int]]:
    """Legacy backend format for backwards compatibility with pqca<=2.0.0

    Use the Legacy mode on pqca>3.0.0 to use it. Refer to the migration guide in the documentation.

    Transform a qiskit backend into a backend suitable for an Automaton in Legacy Mode.

    Args:
        backend (qisket backend, optional): A qiskit backend. Defaults to Aer.

    Raises:
        exceptions.BackendError: Any non-successful result will be raised as an exception.

    Returns:
        Callable[[QuantumCircuit], List[int]]: A function that evaluates a given circuit, returning the list of classical bits.
    """

    from qiskit_ibm_runtime import SamplerV2 as Sampler
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    if backend in None:
        from qiskit_ibm_runtime.fake_provider import FakeManilaV2
        backend = FakeManilaV2()

    def run_circuit_on_backend(circuit: QuantumCircuit) -> List[int]:
        circuit.measure_all()
        sampler = Sampler(mode=backend)
        pm = generate_preset_pass_manager(
            backend=backend, optimization_level=1)
        isa_circuit = pm.run(circuit)
        results = sampler.run([isa_circuit], shots=1).result()
        final_state_as_string = list(results[0].data.meas.get_counts())[0]
        return [int(x) for x in final_state_as_string[::-1]]
    return run_circuit_on_backend


# Currently Rigetti's python libraries do not support converting from Qasm to Quil
# You can, however, use the website / javascript library found at
# https://quantum-circuit.com/qasm2pyquil
# to create a python snippet that builds the circuit.

"""
The MIT License (MIT)

Copyright (c) 2021 Hector Miller-Bakewell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
