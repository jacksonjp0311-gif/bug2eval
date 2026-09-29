def safe_divide(a, b):
    if b == 0:
        raise ValueError("denominator cannot be zero")
    return a / b
