import threading

import expiringdict
import markovify


class ModelCache(object):
    def __init__(self, max_len=1, max_age_seconds=60):
        self.model_fns = {}
        self.cache = expiringdict.ExpiringDict(
            max_len=max_len, max_age_seconds=max_age_seconds
        )
        self.lock = threading.Lock()

    def add_fn(self, name, fn):
        self.model_fns[name] = fn

    def get(self, name):
        model = self.cache.get(name)
        if model is not None:
            return model

        model_fn = self.model_fns.get(name)
        if model_fn is None:
            return None

        self.cache[name] = None

        with open(model_fn) as f:
            model = markovify.NewlineText(f)

        self.cache[name] = model

        return model
