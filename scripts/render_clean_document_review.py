"""Create a private image/reference viewer with no OCR comparison output."""
import html
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.evaluation/clean_document_diagnostic'


def main():
    manifest = json.loads((DATA / 'candidate-manifest.json').read_text(encoding='utf-8'))
    destination = DATA / 'review'
    if destination.exists():
        raise ValueError('Preserve the existing viewer; no review state is overwritten')
    (destination / 'images').mkdir(parents=True)
    cards = []
    for number, page in enumerate(manifest['candidates'], 1):
        source = Path(page['image'])
        if hashlib.sha256(source.read_bytes()).hexdigest() != page['image_sha256']:
            raise ValueError('Source image hash differs')
        filename = f'{number:02d}-' + page['track'] + '-' + page['id'].replace('/', '-') + '.png'
        with Image.open(source) as image:
            if image.getexif().get(274, 1) not in (None, 1):
                raise ValueError('Unexpected orientation; inspect the source explicitly')
            image.convert('RGB').save(destination / 'images' / filename)
        title = html.escape(page['track'] + ' / ' + page['id'])
        reference = html.escape(page['reference'])
        policy = html.escape(page['reference_policy'])
        cards.append(f'<section><h2>{number}. {title}</h2><p>{policy}. '
            'No new human verification; no OCR predictions displayed.</p>'
            f'<div class="pair"><a href="images/{filename}"><img src="images/{filename}" '
            f'alt="{title}"></a><pre>{reference}</pre></div></section>')
    title = 'Focused document diagnostic: private candidate review'
    document = (
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        f'<title>{title}</title><style>body{{font:16px system-ui;margin:2rem;color:#17202a}}'
        '.pair{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:2rem}'
        'img{width:100%;height:auto}pre{white-space:pre-wrap;font:16px/1.7 system-ui}'
        'section{border-top:1px solid #bbb;padding:1.5rem 0;margin:2rem 0}'
        '@media(max-width:800px){.pair{grid-template-columns:1fr}}</style>'
        f'<h1>{title}</h1><p>Candidate selection token: {manifest["selection_token"]}</p>'
        '<p>This viewer contains private images and transcripts. The image screen checks '
        'readability and obstruction, not independently verified ground truth. Click an '
        'image for native resolution. The source datasets and prior review browser are unchanged.</p>'
        + ''.join(cards) + '</html>')
    (destination / 'index.html').write_text(document, encoding='utf-8')
    print(destination / 'index.html')


if __name__ == '__main__':
    main()
