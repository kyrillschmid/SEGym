from diff_patch_search.primes import generate

def test_generate_with_1():
    assert generate(1) == []

def test_generate_with_2():
    assert generate(2) == [2]

def test_generate_with_3():
    assert generate(3) == [3]

def test_generate_with_4():
    assert generate(4) == [2, 2]

def test_generate_with_5():
    assert generate(5) == [5]

def test_generate_with_6():
    assert generate(6) == [2, 3]

def test_generate_with_7():
    assert generate(7) == [7]
