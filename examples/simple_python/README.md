# Simple Python example

```bash
bug2eval capture \
  --id EXAMPLE-001 \
  --title "safe_divide rejects zero denominator" \
  --before-dir examples/simple_python/before \
  --after-dir examples/simple_python/after \
  --verify "python verify.py" \
  --output /tmp/EXAMPLE-001
```
