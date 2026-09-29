"""Record real CLI output and render an 18-second GIF/MP4 replay.

Development-only dependencies: Pillow, imageio-ffmpeg. Run from any directory.
Paths are abbreviated; output is real, while playback pacing is edited.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

repo = Path(__file__).resolve().parents[1]
assets = repo / 'assets'
os.environ['PATH'] = str(Path(sys.executable).parent) + os.pathsep + os.environ['PATH']
font_path = next((p for p in [Path('C:/Windows/Fonts/consola.ttf'), Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')] if p.exists()), None)
font = ImageFont.truetype(str(font_path), 23) if font_path else ImageFont.load_default(size=23)
title_font = ImageFont.truetype(str(font_path), 38) if font_path else ImageFont.load_default(size=38)
small = ImageFont.truetype(str(font_path), 18) if font_path else ImageFont.load_default(size=18)
records = []
with tempfile.TemporaryDirectory(prefix='bug2eval-demo-') as tmp:
    case = str(Path(tmp) / 'B2E-001')
    commands = [
        ['capture', '--id', 'B2E-001', '--title', 'Archive packs itself', '--before-ref', '1652799', '--after-ref', 'ddec8ed', '--verify', 'python benchmarks/verifiers/B2E-001.py', '--output', case],
        ['validate', case],
        ['pack', case],
        ['validate', case + '.b2e'],
    ]
    for argv in commands:
        cp = subprocess.run([sys.executable, '-m', 'bug2eval', *argv], cwd=repo, capture_output=True, text=True, check=True)
        display_argv = [arg.replace(tmp, '$DEMO') for arg in argv]
        stdout = cp.stdout.replace(tmp, '$DEMO')
        records.append({'argv': ['python', '-m', 'bug2eval', *display_argv], 'stdout': stdout, 'stderr': cp.stderr, 'exit_code': cp.returncode})
(assets / 'demo-transcript.json').write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')

cards = [
    ('01 / CAPTURE A REAL BUG', [
        '$ python -m bug2eval capture --id B2E-001',
        '    --title "Archive packs itself"',
        '    --before-ref 1652799 --after-ref ddec8ed',
        '    --verify "python benchmarks/verifiers/B2E-001.py"',
        '    --output $DEMO/B2E-001', '',
        *records[0]['stdout'].replace('\\', '/').splitlines()]),
    ('02 / PROVE THE FIX', ['$ python -m bug2eval validate $DEMO/B2E-001', '', *records[1]['stdout'].splitlines()]),
    ('03 / ONE PORTABLE EVAL', ['$ python -m bug2eval pack $DEMO/B2E-001', *records[2]['stdout'].replace('\\', '/').splitlines(), '', '$ python -m bug2eval validate $DEMO/B2E-001.b2e', *records[3]['stdout'].splitlines()]),
]
frames = []
for index, (heading, lines) in enumerate(cards):
    im = Image.new('RGB', (1280, 720), '#0b1020')
    d = ImageDraw.Draw(im)
    d.text((58, 34), 'Bug2Eval', fill='#eef4ff', font=title_font)
    d.text((58, 88), 'A real bug becomes a reusable agent eval.', fill='#a8b8d3', font=font)
    d.rounded_rectangle((40, 147, 1240, 626), radius=18, fill='#131d30', outline='#2b3e5b', width=2)
    for x, color in [(69, '#f57479'), (95, '#e7bd62'), (121, '#66d4ac')]:
        d.ellipse((x, 170, x+12, 182), fill=color)
    d.text((162, 160), heading, fill='#66d4ac', font=font)
    y = 219
    for line in lines:
        color = '#79e3ba' if 'VALID' in line or 'exit 0' in line else '#e6edf8'
        if line.startswith('$') or line.startswith('    --'):
            color = '#91bdff'
        d.text((69, y), line, fill=color, font=font)
        y += 39
    d.text((58, 653), 'github.com/jacksonjp0311-gif/bug2eval', fill='#e6edf8', font=font)
    d.text((58, 688), 'Recorded CLI output | abbreviated paths | edited pacing', fill='#8596b2', font=small)
    frames.append(im)
frames[0].save(assets / 'bug2eval-demo.gif', save_all=True, append_images=frames[1:], duration=[6000]*3, loop=0, optimize=False)
frames[1].save(assets / 'demo-preview.png')
writer = imageio_ffmpeg.write_frames(str(assets / 'bug2eval-demo.mp4'), (1280, 720), fps=24, codec='libx264', pix_fmt_in='rgb24', pix_fmt_out='yuv420p', output_params=['-movflags', '+faststart'], ffmpeg_log_level='error')
writer.send(None)
for frame in frames:
    for _ in range(144):
        writer.send(frame.tobytes())
writer.close()
print('Recorded four successful CLI commands; generated GIF and 18-second MP4.')
