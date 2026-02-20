OPENQASM 2.0;
include "qelib1.inc";

qreg q[4]; // 3 qubits for estimation, 1 target qubit
creg c[3];

// Initialize target qubit to |1>
x q[3];

// Hadamard on estimation qubits
h q[0];
h q[1];
h q[2];

// Controlled-U operations (T-gates for phase estimation)
// q[0] -> 2^0 rotations
cp(pi/4) q[0], q[3];

// q[1] -> 2^1 rotations
cp(pi/4) q[1], q[3];
cp(pi/4) q[1], q[3];

// q[2] -> 2^2 rotations
cp(pi/4) q[2], q[3];
cp(pi/4) q[2], q[3];
cp(pi/4) q[2], q[3];
cp(pi/4) q[2], q[3];

barrier q;

// Inverse QFT
h q[0];
cp(-pi/2) q[0], q[1];
h q[1];
cp(-pi/4) q[0], q[2];
cp(-pi/2) q[1], q[2];
h q[2];

measure q[0] -> c[0];
measure q[1] -> c[1];
measure q[2] -> c[2];
