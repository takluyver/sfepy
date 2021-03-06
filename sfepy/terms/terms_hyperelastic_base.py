import numpy as nm
from sfepy.terms.terms import Term, terms

_msg_missing_data = 'missing family data!'

class HyperElasticBase(Term):
    """
    Base class for all hyperelastic terms in TL/UL formulation.

    `HyperElasticBase.__call__()` computes element contributions given either
    stress (-> rezidual) or tangent modulus (-> tangent sitffnes matrix),
    i.e. constitutive relation type (CRT) related data. The CRT data are
    computed in subclasses implementing particular CRT (e.g. neo-Hookean
    material), in self.compute_crt_data().

    Modes:

      - 0: total formulation
      - 1: updated formulation

    Notes
    -----
    This is not a proper Term!
    """
    arg_types = ('material', 'virtual', 'state')
    arg_shapes = {'material' : '1, 1', 'virtual' : ('D', 'state'),
                  'state' : 'D'}

    @staticmethod
    def integrate(out, val_qp, vg, fmode):
        if fmode == 2:
            out[:] = val_qp
            status = 0

        else:
            status = vg.integrate(out, val_qp, fmode)

        return status

    @staticmethod
    def function(out, fun, *args):
        return fun(out, *args)

    def __init__(self, *args, **kwargs):
        Term.__init__(self, *args, **kwargs)

        self.stress_cache = None

    def get_family_data(self, state, cache_name, data_names):
        """
        Notes
        -----
        `data_names` argument is ignored for now.
        """
        name = state.name

        step_cache = state.evaluate_cache.setdefault(cache_name, {})
        cache = step_cache.setdefault(self.arg_steps[name], {})

        vg, _, key = self.get_mapping(state, return_key=True)

        data_key = key + (self.arg_derivatives[name],)

        if data_key in cache:
            out = cache[data_key]

        else:
            out = self.compute_family_data(state)
            cache[data_key] = out

        return out

    def compute_stress(self, mat, family_data, **kwargs):
        out = nm.empty_like(family_data.green_strain)

        get = family_data.get
        fargs = [get(name, msg_if_none=_msg_missing_data)
                 for name in self.family_data_names]

        self.stress_function(out, mat, *fargs, **kwargs)

        return out

    def compute_tan_mod(self, mat, family_data, **kwargs):
        shape = list(family_data.green_strain.shape)
        shape[-1] = shape[-2]
        out = nm.empty(shape, dtype=nm.float64)

        get = family_data.get
        fargs = [get(name, msg_if_none=_msg_missing_data)
                 for name in self.family_data_names]

        self.tan_mod_function(out, mat, *fargs, **kwargs)

        return out

    def get_fargs(self, mat, virtual, state,
                  mode=None, term_mode=None, diff_var=None, **kwargs):
        vg, _ = self.get_mapping(state)

        fd = self.get_family_data(state, self.fd_cache_name,
                                  self.family_data_names)

        if mode == 'weak':
            if diff_var is None:
                stress = self.compute_stress(mat, fd, **kwargs)
                self.stress_cache = stress
                tan_mod = nm.array([0], ndmin=4, dtype=nm.float64)

                fmode = 0

            else:
                stress = self.stress_cache
                if stress is None:
                    stress = self.compute_stress(mat, fd, **kwargs)

                tan_mod = self.compute_tan_mod(mat, fd, **kwargs)
                fmode = 1

            return (self.weak_function,
                    stress, tan_mod, fd.mtx_f, fd.det_f, vg, fmode,
                    self.hyperelastic_mode)

        elif mode in ('el_avg', 'qp'):
            if term_mode == 'strain':
                out_qp = fd.green_strain

            elif term_mode == 'stress':
                out_qp = self.compute_stress(mat, fd, **kwargs)

            else:
                raise ValueError('unsupported term mode in %s! (%s)'
                                 % (self.name, term_mode))

            fmode = {'el_avg' : 1, 'qp' : 2}[mode]

            return self.integrate, out_qp, vg, fmode

        else:
            raise ValueError('unsupported evaluation mode in %s! (%s)'
                             % (self.name, mode))

    def get_eval_shape(self, mat, virtual, state,
                       mode=None, term_mode=None, diff_var=None, **kwargs):
        n_el, n_qp, dim, n_en, n_c = self.get_data_shape(state)
        sym = dim * (dim + 1) / 2

        if mode != 'qp':
            n_qp = 1

        return (n_el, n_qp, sym, 1), state.dtype

class DeformationGradientTerm(Term):
    r"""
    Deformation gradient :math:`\ull{F}` in quadrature points for
    `term_mode='def_grad'` (default) or the jacobian :math:`J` if
    `term_mode='jacobian'`.

    Supports 'eval', 'el_avg' and 'qp' evaluation modes.

    :Definition:

    .. math::
        \ull{F} = \pdiff{\ul{x}}{\ul{X}}|_{qp}
        = \ull{I} + \pdiff{\ul{u}}{\ul{X}}|_{qp} \;, \\
        \ul{x} = \ul{X} + \ul{u} \;, J = \det{(\ull{F})}

    :Arguments:
        - parameter : :math:`\ul{u}`
    """
    name = 'ev_def_grad'
    arg_types = ('parameter',)
    arg_shapes = {'parameter' : 'D'}

    @staticmethod
    def function(out, vec, vg, econn, term_mode, fmode):
        d = 1 if term_mode == 'jacobian' else vg.dim
        out_qp = nm.empty((out.shape[0], vg.n_qp, d, d), dtype=out.dtype)

        mode = 1 if term_mode == 'jacobian' else 0
        terms.dq_def_grad(out_qp, vec, vg, econn, mode)

        if fmode == 2:
            out[:] = out_qp
            status = 0

        else:
            status = vg.integrate(out, out_qp, fmode)

        return status

    def get_fargs(self, parameter,
                  mode=None, term_mode=None, diff_var=None, **kwargs):
        ap, vg = self.get_approximation(parameter)

        vec = self.get_vector(parameter)

        fmode = {'eval' : 0, 'el_avg' : 1, 'qp' : 2}.get(mode, 1)

        return vec, vg, ap.econn, term_mode, fmode

    def get_eval_shape(self, parameter,
                       mode=None, term_mode=None, diff_var=None, **kwargs):
        n_el, n_qp, dim, n_en, n_c = self.get_data_shape(parameter)

        if mode != 'qp':
            n_qp = 1

        if term_mode == 'jacobian':
            return (n_el, n_qp, 1, 1), parameter.dtype

        else: # 'def_grad'
            return (n_el, n_qp, dim, dim), parameter.dtype
