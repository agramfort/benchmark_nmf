from benchopt import BaseObjective, safe_import_context

# Protect import to allow manipulating objective without importing library
# Useful for autocompletion and install commands
with safe_import_context() as import_ctx:
    import numpy as np
    from scipy.special import kl_div
    # Requires Tensorly >=0.8, postpone implementation
    # TODO
    # import tensorly
    # from tensorly.cp_tensor import cp_normalize, cp_permute_factors


class Objective(BaseObjective):
    min_benchopt_version = "1.3"
    name = "Nonnegative Matrix Factorization"
    is_convex = False

    # All parameters 'p' defined here are available as 'self.p'
    parameters = {
        'share_init': [True],
    }

    # install_cmd = 'conda'
    # requirements = [
    #     'pip:git+https://github.com/tensorly/tensorly@main'
    # ]

    def get_one_solution(self):
        # Return one solution. This should be compatible with 'self.compute'.
        n, m = self.X.shape
        return np.zeros((n, self.rank)), np.zeros((self.rank, m))

    def set_data(self, X, rank, true_factors=None):
        # The keyword arguments of this function are the keys of the `data`
        # dict in the `get_data` function of the dataset.
        # They are customizable.
        # TODO: handle W and H known in only some cases, to track source
        # identification
        self.X = X
        self.rank = rank
        self.true_factors = true_factors

    def compute(self, factors):
        # The arguments of this function are the outputs of the
        # `get_result` method of the solver.
        # They are customizable.
        W, H = factors
        WH = np.dot(W,H)
        frobenius_loss = 1/2*np.linalg.norm(self.X - WH)**2
        kl_loss = np.sum(kl_div(self.X, WH))

        output_dic = {
            'frobenius': frobenius_loss,
            'kl': kl_loss, 
        }

        if self.true_factors:
            #  compute factor match score
            #  first, solve permutation and scaling ambiguity
            W_true, H_true = self.true_factors
            Ht = H.T
            Ht_true = H_true.T

            # tensorly version, requires Tensorly >= 0.8
            # factors_tl = [W, Ht]
            # factors_tl_true = [W_true, Ht_true]
            # factors_tl = cp_normalize((None,factors_tl))
            # factors_tl_true = cp_normalize((None,factors_tl_true))
            # _, factors_tl = cp_permute_factors(
            #     (None,factors_tl_true), (None,factors_tl)
            # )[0]
            # fms = np.prod(
            #     np.diag(factors_tl[0].T@factors_tl_true[0])*
            #     np.diag(factors_tl[1].T@factors_tl_true[1])
            # )

            # native version
            W = W/np.linalg.norm(W, axis=0)
            Ht = Ht/np.linalg.norm(Ht, axis=0)
            W_true = W_true/np.linalg.norm(W_true, axis=0)
            Ht_true = Ht_true/np.linalg.norm(Ht_true, axis=0)
            # TODO: suboptimal permutation for now, want to use tensorly
            # but it is bugged
            perms = np.argmax((W.T@W_true)*(Ht.T@Ht_true), axis=1)
            W = W[:, perms]
            Ht = Ht[:, perms]
            factor_match_score = np.prod(np.diag(W.T@W_true)*np.diag(Ht.T@Ht_true))

            output_dic.update({
                'factor_match_score': factor_match_score
                })
        return output_dic

    def get_objective(self, random_state=27):
        # The output of this function are the keyword arguments
        # for the `set_objective` method of the solver.
        # They are customizable.
        # we compute a random seeded init here to share across methods!
        m, n = self.X.shape
        rank = self.rank
        if self.share_init:
            rng = np.random.RandomState(random_state)
            factors_init = [rng.rand(m, rank), rng.rand(rank, n)]
            for factor in factors_init:
                factor.flags.writeable = False  # Read Only
        else:
            factors_init = None
        return dict(X=self.X, rank=self.rank, factors_init=factors_init)
