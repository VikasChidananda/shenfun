r"""
Solve Poisson equation in 2D with periodic bcs in one direction
and homogeneous Neumann in the other

    \nabla^2 u = f,

Use Fourier basis for the periodic direction and Shen's Neumann basis for the
non-periodic direction.

The equation to solve is

     (\nabla^2 u, v) = (f, v)

"""
import sys
import os
import sympy as sp
import numpy as np
from shenfun import inner, div, grad, TestFunction, TrialFunction, \
    TensorProductSpace, FunctionSpace, Array, Function, comm, la, dx, \
    chebyshev

# Collect basis and solver from either Chebyshev or Legendre submodules
assert len(sys.argv) == 3, "Call with two command-line arguments"
assert sys.argv[-1].lower() in ('legendre', 'chebyshev', 'chebyshevu')
assert isinstance(int(sys.argv[-2]), int)

family = sys.argv[-1].lower()
Solver = chebyshev.la.Helmholtz if family == 'chebyshev' else la.SolverGeneric1ND

# Use sympy to compute a rhs, given an analytical solution
x, y = sp.symbols("x,y", real=True)
ue = sp.cos(2*sp.pi*x)
fe = -ue.diff(x, 2)-ue.diff(y, 2)

# Size of discretization
N = int(sys.argv[-2])
N = (N, N)
bc = {'left': ('N', ue.diff(x, 1).subs(x, -1)), 'right': ('N', ue.diff(x, 1).subs(x, 1))}
SN = FunctionSpace(N[0], family=family, bc=bc)
K1 = FunctionSpace(N[1], family='F', dtype='d')
T = TensorProductSpace(comm, (SN, K1), axes=(0, 1))
u = TrialFunction(T)
v = TestFunction(T)

# Get f on quad points
fj = Array(T, buffer=fe)

# Compute right hand side of Poisson equation
f_hat = inner(v, fj)

# Get left hand side of Poisson equation
matrices = inner(v, -div(grad(u)))

# Create Helmholtz linear algebra solver
sol = Solver(matrices)

constraint = ((0, dx(Array(T, buffer=ue), weighted=True)/dx(Array(T, val=1), weighted=True)),)

# Solve and transform to real space
u_hat = Function(T).set_boundary_dofs()           # Solution spectral space
u_hat = sol(f_hat, u_hat, constraints=constraint)

uq = T.backward(u_hat).copy()

# Compare with analytical solution
uj = Array(T, buffer=ue)
print(abs(uj-uq).max())
assert np.allclose(uj, uq)

if 'pytest' not in os.environ:
    import matplotlib.pyplot as plt
    plt.figure()
    X = T.local_mesh(True) # With broadcasting=True the shape of X is local_shape, even though the number of datapoints are still the same as in 1D
    plt.contourf(X[0], X[1], uq)
    plt.colorbar()

    plt.figure()
    plt.contourf(X[0], X[1], uj)
    plt.colorbar()

    plt.figure()
    plt.contourf(X[0], X[1], uq-uj)
    plt.colorbar()
    plt.title('Error')

    plt.show()
