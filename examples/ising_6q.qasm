OPENQASM 2.0;
include "qelib1.inc";

qreg q[6];
creg c[6];

// 1. Apply external magnetic field (Partial Rotations)
ry(pi/3) q[0];
ry(pi/3) q[1];
ry(pi/3) q[2];
ry(pi/3) q[3];
ry(pi/3) q[4];
ry(pi/3) q[5];

// 2. Simulate electron/spin interactions (Linear Entanglement)
cx q[0], q[1];
cx q[1], q[2];
cx q[2], q[3];
cx q[3], q[4];
cx q[4], q[5];

measure q -> c;
