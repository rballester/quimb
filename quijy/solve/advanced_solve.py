"""
Interface to slepc4py for solving advanced eigenvalue problems.
"""
# TODO: documentation
# TODO: get eigenvectors
# TODO: mimick seivals interface
# TODO: delete solver or keep and extend
# TODO: FEAST / other solvers
from petsc4py import PETSc
from slepc4py import SLEPc
import numpy as np


def scipy_to_petsc_csr(a):
    """ Convert a scipy.sp_csrmatrix to PETSc csr matrix. """
    b = PETSc.Mat().createAIJ(size=a.shape, csr=(a.indptr, a.indices, a.data))
    return b


def aeigsys_solver(which="LM", sigma=None, isherm=True, extra_evals=False):
    """ Create an advanced eigensystem solver

    Parameters
    ----------
        sigma: target eigenvalue
        isherm: whether problem is hermitian or not
        extra_evals: whether to return converged eigenpairs beyond requested
            subspace size

    Returns
    -------
        SLEPc solver ready to be called. """
    which = "TM" if sigma is not None else which
    scipy_to_slepc_which = {
        "LM": SLEPc.EPS.Which.LARGEST_MAGNITUDE,
        "SM": SLEPc.EPS.Which.SMALLEST_MAGNITUDE,
        "LR": SLEPc.EPS.Which.LARGEST_REAL,
        "SR": SLEPc.EPS.Which.SMALLEST_REAL,
        "LI": SLEPc.EPS.Which.LARGEST_IMAGINARY,
        "SI": SLEPc.EPS.Which.SMALLEST_IMAGINARY,
        "TM": SLEPc.EPS.Which.TARGET_MAGNITUDE,
        "TR": SLEPc.EPS.Which.TARGET_REAL,
        "TI": SLEPc.EPS.Which.TARGET_IMAGINARY,
    }
    slepc_isherm = {
        True: SLEPc.EPS.ProblemType.HEP,
        False: SLEPc.EPS.ProblemType.NHEP,
    }
    eigensolver = SLEPc.EPS()
    eigensolver.create()
    eigensolver.setType('krylovschur')
    eigensolver.setProblemType(slepc_isherm[isherm])
    eigensolver.setWhichEigenpairs(scipy_to_slepc_which[which])
    eigensolver.setConvergenceTest(SLEPc.EPS.Conv.ABS)
    return eigensolver


def aeigsys(a, k=6, which="LM", sigma=None, isherm=True,
            extra_evals=False):
    """ Solve a matrix using the advanced eigensystem solver

    Parameters
    ----------
        a: sparse matrix in csr format
        k: number of requested eigenpairs
        sigma: target eigenvalue
        isherm: whether problem is hermitian or not
        extra_evals: whether to return converged eigenpairs beyond requested
            subspace size

    Returns
    -------
        lk: eigenvalues """
    eigensolver = aeigsys_solver(which=which, sigma=sigma, isherm=isherm,
                                 extra_evals=extra_evals)
    A = scipy_to_petsc_csr(a)
    eigensolver.setOperators(A)
    eigensolver.setDimensions(k)
    eigensolver.solve()
    nconv = eigensolver.getConverged()
    assert nconv >= k
    k = nconv if extra_evals else k
    l = np.asarray([eigensolver.getEigenvalue(i).real for i in range(k)]).real
    l = np.sort(l)
    eigensolver.destroy()
    return l


def internal_eigsys_solver(k=6, sigma=0.0, tol=None):
    # LINEAR SOLVER AND PRECONDITIONER
    P = PETSc.PC()
    P.create()
    P.setType('lu')
    P.setFactorSolverPackage('mumps')
    K = PETSc.KSP()
    K.create()
    K.setPC(P)
    K.setType('preonly')
    # SPECTRAL TRANSFORMER
    S = SLEPc.ST()
    S.create()
    S.setKSP(K)
    S.setType('sinvert')
    S.setShift(sigma)
    # EIGENSOLVER
    eigensolver = SLEPc.EPS()
    eigensolver.create()
    eigensolver.setST(S)
    eigensolver.setProblemType(SLEPc.EPS.ProblemType.HEP)
    eigensolver.setType('krylovschur')
    eigensolver.setWhichEigenpairs(SLEPc.EPS.Which.TARGET_MAGNITUDE)
    eigensolver.setTarget(sigma)
    eigensolver.setDimensions(k)
    eigensolver.setConvergenceTest(SLEPc.EPS.Conv.ABS)
    eigensolver.setTolerances(tol=tol, max_it=None)
    return eigensolver


def internal_eigvals(a, k=6, sigma=0.0, tol=None, extra_evals=False):
    A = scipy_to_petsc_csr(a)
    eigensolver = internal_eigsys_solver(k=k, sigma=sigma, tol=tol)
    eigensolver.setOperators(A)
    eigensolver.solve()
    nconv = eigensolver.getConverged()
    assert nconv >= k
    k = nconv if extra_evals else k
    l = np.asarray([eigensolver.getEigenvalue(i).real for i in range(k)]).real
    l = np.sort(l)
    eigensolver.destroy()
    return l
