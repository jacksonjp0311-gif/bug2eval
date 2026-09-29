# Launch kit

Repository: https://github.com/jacksonjp0311-gif/bug2eval

## X draft

I built Bug2Eval: turn a fixed bug into a portable eval for coding agents.

Broken snapshot + fixed snapshot + the same verifier.
Before fails. After passes. One .b2e file.

Launching with 3 real bugs from Bug2Eval itself.

https://github.com/jacksonjp0311-gif/bug2eval

Attach `assets/bug2eval-demo.mp4` (18 seconds, H.264, 1280x720). The GIF is embedded
in the README. These files replay recorded CLI output, with abbreviated local paths
and edited pacing. No model solve or speed claim is implied. The post is a draft.

## Optional PyPI publication

The package is version 0.1.3. No PyPI credentials or trusted publisher are configured
in this release environment, so no PyPI upload was attempted.

To publish after configuring PyPI authentication in your environment:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/bug2eval-0.1.3*
python -m twine upload dist/bug2eval-0.1.3*
```

Never commit tokens. The README uses a GitHub install until the package is actually
published. Check project-name availability again immediately before uploading.
