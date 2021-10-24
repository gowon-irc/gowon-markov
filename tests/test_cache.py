import time

from gowon_markov import cache


def test_cache_expiration(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data="I'm the model."))

    c = cache.ModelCache(max_age_seconds=0.1)
    c.add_fn("m", "model.txt")

    model = c.get("m")
    model2 = c.get("m")

    assert model is not None
    assert model is model2

    time.sleep(0.11)

    model3 = c.get("m")

    assert model3 is not model


def test_cache_replaced(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data="I'm the model."))

    c = cache.ModelCache(max_len=1, max_age_seconds=60)
    c.add_fn("m1", "model1.txt")
    c.add_fn("m2", "model2.txt")

    model1 = c.get("m1")
    model2 = c.get("m1")

    assert model1 is model2

    model3 = c.get("m2")
    model4 = c.get("m1")

    assert model4 is not model1


def test_cache_in_fixture(mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data="I'm the model."))

    c = cache.ModelCache(max_len=1, max_age_seconds=60)
    c.add_fn("m1", "model1.txt")
    c.add_fn("m2", "model2.txt")

    def gen_f(c):
        def f(k):
            return c.get(k)

        return f

    f = gen_f(c)

    model1 = f("m1")
    model2 = f("m1")

    assert model1 is model2

    model3 = f("m2")
    model4 = f("m1")

    assert model4 is not model1
