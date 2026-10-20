"""Freeze a small input-screened diagnostic without reading OCR predictions."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unicodedata

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / '.evaluation/clean_document_diagnostic'
PROTOCOL = ROOT / 'benchmarks/accuracy/CLEAN_DOCUMENT_DIAGNOSTIC_PROTOCOL.md'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def khmer_letter_marks(text):
    return sum(0x1780 <= ord(c) <= 0x17D3 and unicodedata.category(c)[0] in 'LM'
               for c in text)


def business_reasons(reference, dimensions):
    reasons = []
    if reference['uncertain_spans']:
        reasons.append('recorded_reference_uncertainty')
    if '[ILLEGIBLE]' in reference['transcript']:
        reasons.append('literal_unreadable_marker')
    if khmer_letter_marks(reference['transcript']) < 50:
        reasons.append('fewer_than_50_khmer_letters_and_marks')
    if min(dimensions) < 500 or max(dimensions) < 1000:
        reasons.append('below_declared_image_dimensions')
    return reasons


def image_metadata(path, expected):
    if digest(path) != expected:
        raise ValueError('Image source differs: ' + str(path))
    with Image.open(path) as image:
        image.load()
        if image.width <= 0 or image.height <= 0:
            raise ValueError('Empty image')
        return [image.width, image.height]


def main():
    if DATA.exists():
        raise ValueError('Preserve the existing frozen selection; preparation is one-time')
    expanded_path = ROOT / '.evaluation/expanded_ocr/prepared.json'
    reference_path = ROOT / '.evaluation/business_ocr/references.jsonl'
    source_selection_path = ROOT / '.evaluation/kh_funsd_local/page-selection.json'
    expanded = read(expanded_path)
    source = {p['id']: p for p in read(source_selection_path)['pages']}
    references = [json.loads(line) for line in reference_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(references) != 146 or len({r['id'] for r in references}) != 146:
        raise ValueError('Business source coverage differs')
    candidates, exclusions = [], []
    for group in expanded['groups']:
        if group['dataset'] != 'khob':
            continue
        if not group['source_id'].startswith('task-1/'):
            exclusions.append(dict(track='khob-digital', id=group['source_id'], reasons=['other_acquisition']))
            continue
        if len(group['units']) != 1:
            raise ValueError('Expected one full-page KHOB unit')
        unit = group['units'][0]
        path = ROOT / '.evaluation' / group['image']
        dimensions = image_metadata(path, group['image_sha256'])
        candidates.append(dict(track='khob-digital', id=unit['id'], group=group['group'],
            image=str(path.resolve()), image_sha256=group['image_sha256'], dimensions=dimensions,
            reference=unit['reference'], reference_sha256=text_digest(unit['reference']),
            reference_policy='Existing upstream transcript; no new independent human review',
            human_reviewed=False, reference_complete=False))
    for reference in sorted(references, key=lambda r: r['id']):
        page = source[reference['id']]
        path = ROOT / '.evaluation/kh_funsd_local' / page['image']
        dimensions = image_metadata(path, reference['image_sha256'])
        if dimensions != page['upright_dimensions']:
            raise ValueError('Upright source geometry differs')
        if text_digest(reference['transcript']) != reference['draft_sha256']:
            raise ValueError('Reference source hash differs')
        if reference['human_reviewed'] or reference['reference_complete']:
            raise ValueError('Expected unchanged, unreviewed operational references')
        reasons = business_reasons(reference, dimensions)
        metadata = dict(track='khfunsd-screened', id=reference['id'],
            category=page['category'], acquisition_folder=page['acquisition_folder'],
            dimensions=dimensions, khmer_letter_marks=khmer_letter_marks(reference['transcript']))
        if reasons:
            exclusions.append(dict(metadata, reasons=reasons))
            continue
        candidates.append(dict(metadata, group=reference['id'], image=str(path.resolve()),
            image_sha256=reference['image_sha256'], reference=reference['transcript'],
            reference_sha256=reference['draft_sha256'],
            reference_policy='Unreviewed machine-generated operational ground truth',
            human_reviewed=False, reference_complete=False))
    candidates.sort(key=lambda p: (p['track'], p['id']))
    khob = [p for p in candidates if p['track'] == 'khob-digital']
    if len(khob) != 10 or len({p['group'] for p in khob}) != 10:
        raise ValueError('KHOB selection must contain exactly ten distinct source groups')
    source_hashes = {str(p.relative_to(ROOT)): digest(p) for p in
        [PROTOCOL, Path(__file__), expanded_path, reference_path, source_selection_path]}
    manifest = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
        design='Post hoc input-screened diagnostic; previous results already known',
        sources=source_hashes, selection_reads_predictions=False, candidates=candidates,
        exclusions=exclusions,
        eligible_by_track=dict(Counter(p['track'] for p in candidates)),
        required_visual_screen='Assistant image/reference screen; no prediction access; no human-gold claim')
    manifest['selection_token'] = text_digest(json.dumps(manifest, sort_keys=True, ensure_ascii=False))
    DATA.mkdir(parents=True)
    write(DATA / 'candidate-manifest.json', manifest)
    write(DATA / 'visual-screen.template.json', dict(selection_token=manifest['selection_token'],
        screener='Codex assistant; not independent human review', reviewed_against_predictions=False,
        decisions=[dict(track=p['track'], id=p['id'], decision='pending', reason='') for p in candidates]))
    (DATA / 'protocol.md').write_bytes(PROTOCOL.read_bytes())
    print(json.dumps(dict(selection_token=manifest['selection_token'],
        eligible_by_track=manifest['eligible_by_track'], excluded=len(exclusions)), indent=2))


if __name__ == '__main__':
    main()
