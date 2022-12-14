# -*- coding: utf-8 -*-

import itertools
import numpy as np
import torch


class DiscreteExpFamily:

    def __init__(self, m) -> None:
        """
        Base class for (constrained) exponential family distributions.
        When subclassing, one must at least implement the `states` function.
        :param m: dimensionality
        """
        super().__init__()
        self.m = m
        self._states = None  # lazy initialization of this

    @property
    def states(self):
        """ Returns a matrix of possible states (states in cal{C}), organized by rows"""
        raise NotImplementedError()

    @property
    def n_states(self):
        return len(self.states)

    def weights(self, theta):
        """Vector of un-normalized weights"""
        # [252, 10] @ [10] -> [252]
        return self.states @ theta

    def log_partition(self, theta):
        # scalar
        return torch.log(torch.sum(torch.exp(self.weights(theta))))

    def pmf(self, theta):
        """Probability mass (vector)"""
        # [252] - scalar
        # <theta, state> - log sum_{s'} exp <theta, s'>
        return torch.exp(self.weights(theta) - self.log_partition(theta))

    def marginals(self, theta):
        """Basic implementation for the marginal (aka the expected value of this random variable)"""
        return self.pmf(theta) @ self.states

    def sample(self, theta, rng=None):
        """
        Base implementation of (faithful) sampling
        """
        if rng is None:
            rng = np.random.RandomState()
        _pmft = self.pmf(theta)

        # print('YYY', _pmft)

        n_states = self.n_states
        indx_ch = rng.choice(list(range(n_states)), p=_pmft.detach().cpu().numpy())
        res = self.states[indx_ch]

        # print('XXX', res)

        return res

    def sample_f(self, rng):
        """
        functional version of sampling (useful for setting the random generator)
        """
        return lambda th: self.sample(th, rng)

    def map(self, theta):
        """
        Basic (inefficient) implementation of map function (returns 1 state)
        """
        return self.states[torch.argmax(self.weights(theta))]

    def perturb_and_map(self, noise_f):
        def _pam(theta, ctx=None):
            if hasattr(ctx, 'eps'):
                eps = ctx.eps
            else:
                eps = torch.stack([noise_f() for _ in range(self.m)])
                if ctx is not None:
                    try:
                        ctx.eps = eps
                    except AttributeError:
                        print('Problems with ctx')
            theta_prime = theta + eps
            return self.map(theta_prime)
        return _pam

    def grad_log_p(self, mu_f=None):
        """Gradient of the log probability:
        \nabla log p(z, theta) = \nabla [<z, theta>  - A(theta)] = z - mu(theta).
        Use `mu_f` for approximate computation, otherwise uses full marginals.
        Returns a function (to be used with the score function estimator)"""
        if mu_f is None:
            mu_f = self.marginals

        def _glp(theta, ctx=None):
            # mu_f takes a theta and returns the marginals
            mu_theta = mu_f(theta)  # here surely you don't want to use the same sample!
            assert hasattr(ctx, 'sample'), 'must save the forward value with ctx.sample!'
            return ctx.sample - mu_theta
        return _glp


class TopK(DiscreteExpFamily):

    def __init__(self, m,  k, device=None) -> None:
        super().__init__(m)
        self.k = k
        self.device = device

    @property
    def states(self):
        # TODO implement an iterator version of this (with yield, so that it scales in memory)
        if self._states is None:
            n, k = self.m, self.k
            combs = list(itertools.combinations(range(n), k))
            n_states = len(combs)
            assert n_states == np.math.factorial(n)/(np.math.factorial(k)*np.math.factorial(n-k))
            print('Number of possible states:', n_states)
            mat_x = np.zeros((len(combs), n))
            for i in range(n_states):
                mat_x[i, combs[i]] = 1.
            self._states = torch.from_numpy(mat_x).float().to(self.device)

        return self._states

    def map_2d(self, theta_2d):
        batch_size = theta_2d.shape[0]
        state_2d = torch.zeros((batch_size, self.m), device=self.device)
        ind1_2d = torch.argsort(theta_2d, descending=True).to(self.device)[:, :self.k]
        dim_0 = torch.arange(batch_size, device=self.device).view(-1, 1).repeat(1, self.k).view(-1)
        dim_1 = ind1_2d.reshape(-1)
        state_2d[dim_0, dim_1] = 1.
        return state_2d

    def map(self, theta):
        """Better implementation of map that uses argsort (probably not linear).
        Could do better... but this is fine atm"""
        # theta is a tensor with shape [N]
        state = torch.zeros(self.m, device=self.device)
        ind1 = torch.argsort(theta, descending=True)[:self.k]
        state[ind1] = 1.
        return state


if __name__ == '__main__':
    topk = TopK(10, 5)
    ttheta = 0.1 * torch.randn(10)

    print(f'STATES ({topk.states.shape})', topk.states)

    print(topk.sample(ttheta))
    print(topk.sample(ttheta))
    print(topk.sample(ttheta))

    print()

    print(topk.map(ttheta))
    print(topk.map(ttheta))

    print(topk.marginals(ttheta))