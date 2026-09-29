from calc import safe_divide
try:
    safe_divide(1, 0)
except ValueError:
    raise SystemExit(0)
except Exception as exc:
    print(f"wrong exception: {type(exc).__name__}: {exc}")
    raise SystemExit(1)
print("expected ValueError")
raise SystemExit(1)
