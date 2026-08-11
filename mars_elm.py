"""Minimal MARS (earth-style, degree=1) and ELM implementations.

py-earth / elmNN have no working Python 3.12 build, so the two algorithms the
paper relies on that are missing from scikit-learn are implemented here to match
the R packages the paper used:

  * MARS  -> earth 5.3.0 defaults: degree=1 (additive), penalty=2, nk=min(200,
    max(20, 2*ncol)+1), forward stepwise hinge-pair selection + backward pruning
    on GCV. Variable importance = ``nsubsets`` (number of backward-pass subsets
    containing the variable), which is earth's default importance criterion.
  * ELM   -> elmNN 1.0 defaults: single hidden layer, random input weights and
    biases, radial-basis activation, output weights by Moore-Penrose pseudoinverse.
"""

import numpy as np
from sklearn.base import BaseEstimator, RegressorMixin


def _lstsq_rss(B, y):
    coef, *_ = np.linalg.lstsq(B, y, rcond=None)
    resid = y - B @ coef
    return float(resid @ resid), coef


def _gcv(rss, n, n_terms, penalty):
    # effective parameters: terms + penalty * (terms - 1) / 2  (Friedman 1991)
    c = n_terms + penalty * (n_terms - 1) / 2.0
    denom = 1.0 - c / n
    if denom <= 0:
        return np.inf
    return (rss / n) / (denom ** 2)


class Earth(BaseEstimator, RegressorMixin):
    """Additive MARS with hinge basis functions and GCV backward pruning."""

    def __init__(self, max_terms=None, penalty=2.0, n_knots=20, min_span_frac=0.01):
        self.max_terms = max_terms
        self.penalty = penalty
        self.n_knots = n_knots
        self.min_span_frac = min_span_frac

    # ---- basis bookkeeping -------------------------------------------------
    # each term is (var_index, knot, direction) with direction +1 -> max(0, x-k)
    # and -1 -> max(0, k-x); the intercept is represented by None.
    @staticmethod
    def _eval_term(X, term):
        if term is None:
            return np.ones(X.shape[0])
        j, k, d = term
        if d > 0:
            return np.maximum(0.0, X[:, j] - k)
        return np.maximum(0.0, k - X[:, j])

    def _design(self, X, terms):
        return np.column_stack([self._eval_term(X, t) for t in terms])

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        n, p = X.shape
        max_terms = self.max_terms or min(200, max(20, 2 * p) + 1)

        terms = [None]
        B = self._design(X, terms)
        rss, _ = _lstsq_rss(B, y)
        min_span = max(1, int(self.min_span_frac * n))

        # ---- forward pass: add hinge pairs greedily ------------------------
        while len(terms) + 2 <= max_terms:
            best = None
            for j in range(p):
                xj = X[:, j]
                lo, hi = np.percentile(xj, [5, 95])
                cands = np.unique(np.quantile(xj, np.linspace(0.05, 0.95, self.n_knots)))
                for k in cands:
                    if np.sum(xj > k) < min_span or np.sum(xj < k) < min_span:
                        continue
                    if not (lo <= k <= hi):
                        continue
                    cand_terms = terms + [(j, k, 1), (j, k, -1)]
                    Bc = np.column_stack([B, self._eval_term(X, cand_terms[-2]),
                                          self._eval_term(X, cand_terms[-1])])
                    r, _ = _lstsq_rss(Bc, y)
                    if best is None or r < best[0]:
                        best = (r, j, k, Bc)
            if best is None:
                break
            new_rss, j, k, Bc = best
            # stop when improvement is negligible
            if new_rss > rss * (1 - 1e-4):
                break
            terms = terms + [(j, k, 1), (j, k, -1)]
            B, rss = Bc, new_rss

        # ---- backward pass: prune on GCV, tracking nsubsets ----------------
        cur = list(range(len(terms)))
        best_gcv = _gcv(rss, n, len(cur), self.penalty)
        best_set = list(cur)
        nsubsets = {t: 0 for t in range(len(terms))}
        for t in cur:
            nsubsets[t] += 1  # the full model counts as a subset

        while len(cur) > 1:
            drop_best = None
            for idx in cur:
                if terms[idx] is None:
                    continue  # never drop the intercept
                trial = [i for i in cur if i != idx]
                r, _ = _lstsq_rss(self._design(X, [terms[i] for i in trial]), y)
                g = _gcv(r, n, len(trial), self.penalty)
                if drop_best is None or g < drop_best[0]:
                    drop_best = (g, idx, trial)
            if drop_best is None:
                break
            g, idx, trial = drop_best
            cur = trial
            for t in cur:
                nsubsets[t] += 1
            if g < best_gcv:
                best_gcv, best_set = g, list(cur)

        self.terms_ = [terms[i] for i in best_set]
        self.rss_, self.coef_ = _lstsq_rss(self._design(X, self.terms_), y)
        self.gcv_ = best_gcv

        # earth-style variable importance: number of pruning subsets in which a
        # variable appears, summed over its terms.
        imp = np.zeros(p)
        for i, t in enumerate(terms):
            if t is not None:
                imp[t[0]] += nsubsets[i]
        self.feature_importances_ = imp
        self.n_features_in_ = p
        return self

    def predict(self, X):
        X = np.asarray(X, dtype=float)
        return self._design(X, self.terms_) @ self.coef_


class ELM(BaseEstimator, RegressorMixin):
    """Extreme learning machine, radial-basis activation (elmNN default)."""

    def __init__(self, n_hidden=20, random_state=0):
        self.n_hidden = n_hidden
        self.random_state = random_state

    def fit(self, X, y):
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float).ravel()
        rng = np.random.default_rng(self.random_state)
        p = X.shape[1]
        # radbas in elmNN: centres drawn uniformly, widths positive random
        self.centres_ = rng.uniform(-1, 1, size=(self.n_hidden, p))
        self.widths_ = rng.uniform(0, 1, size=self.n_hidden)
        H = self._hidden(X)
        self.beta_ = np.linalg.pinv(H) @ y
        self.n_features_in_ = p
        return self

    def _hidden(self, X):
        d2 = ((X[:, None, :] - self.centres_[None, :, :]) ** 2).sum(axis=2)
        return np.exp(-(self.widths_[None, :] ** 2) * d2)

    def predict(self, X):
        return self._hidden(np.asarray(X, dtype=float)) @ self.beta_
