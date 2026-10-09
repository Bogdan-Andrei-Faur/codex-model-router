"""Encode deterministic browser frames with a fixed palette; synthetic artwork only."""
import argparse
import json
from pathlib import Path

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frame-ms', type=int, required=True)
    args = parser.parse_args()
    files = sorted(args.frames.glob('*.png'))
    if not files:
        raise ValueError('No browser frames')
    # One palette prevents frame-to-frame gradient/color flicker. Sample across
    # the whole animation so props introduced during a transition are included.
    indices = sorted({round(i * (len(files) - 1) / 11) for i in range(12)})
    with Image.open(files[0]) as first:
        size = first.size
    palette_board = Image.new('RGB', (size[0] * len(indices), size[1]))
    for position, index in enumerate(indices):
        with Image.open(files[index]) as source:
            palette_board.paste(source.convert('RGB'), (position * size[0], 0))
    palette = palette_board.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    frames = []
    for file in files:
        with Image.open(file) as source:
            frames.append(source.convert('RGB').quantize(palette=palette, dither=Image.Dither.NONE))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(args.output, save_all=True, append_images=frames[1:],
                   duration=args.frame_ms, loop=0, optimize=True, disposal=1)
    with Image.open(args.output) as result:
        duration = 0
        for frame in range(result.n_frames):
            result.seek(frame)
            duration += result.info.get('duration', 0)
        assert result.size == size
        assert duration == len(files) * args.frame_ms
        assert result.info.get('loop') == 0
        if len(files) > 1:
            assert result.n_frames > 1, 'Animated preview has no moving frames'
        print(json.dumps({'frames': result.n_frames, 'durationMs': duration,
                          'width': size[0], 'height': size[1],
                          'bytes': args.output.stat().st_size}))


if __name__ == '__main__':
    main()
