"""Contact sheet of the production GIF gallery; synthetic images only."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
GALLERY = ROOT / 'docs/design/companion-animations'


def main():
    previews = json.loads((GALLERY / 'manifest.json').read_text())['previews']
    width, height, columns = 480, 296, 4
    board = Image.new('RGB', (columns * width, ((len(previews)+columns-1)//columns)*height), (11, 13, 14))
    for index, entry in enumerate(previews):
        with Image.open(GALLERY / entry['file']) as image:
            elapsed = 0
            # Show the exit in flight rather than its fully transparent final pose.
            target = 400 if entry['key'] == 'leave' else 1000
            for frame in range(image.n_frames):
                image.seek(frame)
                elapsed += image.info.get('duration', 50)
                if elapsed >= target:
                    break
            board.paste(image.convert('RGB'), ((index % columns)*width, (index//columns)*height))
    board.save(ROOT / 'docs/design/companion-activity-poses.png')
    print(f'Contact sheet: {len(previews)} synthetic poses')


if __name__ == '__main__':
    main()
