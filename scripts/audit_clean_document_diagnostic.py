"""Independently verify the focused selection, raw predictions and distances."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_document_ocr import edit_distance, self_check
from document_ocr_metrics import visible_text

DATA = ROOT / '.evaluation/clean_document_diagnostic'
PUBLIC = ROOT / 'benchmarks/accuracy/clean-document-diagnostic'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(text):
    from khmereasytools import khseg_spans
    text = unicodedata.normalize('NFC', text)
    return dict(compact_cer=''.join(c for c in text if not c.isspace() and c != '\u200b'),
                whitespace_unit_wer=text.replace('\u200b', ' ').split(),
                segmentation_assisted_wer=[s.text for s in khseg_spans(text) if s.kind not in ('whitespace', 'boundary')])


def main():
    result = read(PUBLIC / 'results.json')
    public_selection = read(PUBLIC / 'selection.json')
    frozen = read(DATA / 'final-selection.json')
    counts_path = DATA / 'selected-audited-counts.json'
    counts = read(counts_path)
    manifest = read(DATA / 'candidate-manifest.json')
    review = read(DATA / 'visual-screen.json')
    if (digest(counts_path) != result['private_selected_count_records_sha256'] or
            digest(PUBLIC / 'selection.json') != result['selection_sha256'] or
            digest(DATA / 'final-selection.json') != public_selection['private_final_selection_sha256'] or
            len({o['freeze_token'] for o in [frozen, counts, public_selection, result]}) != 1):
        raise ValueError('Frozen selection/result hashes differ')
    for name, sha in result['source_hashes'].items():
        if digest(ROOT / name) != sha:
            raise ValueError('Audited source file changed')
    for name, sha in manifest['sources'].items():
        if digest(ROOT / name) != sha:
            raise ValueError('Selection source changed')
    refs = [json.loads(line) for line in (ROOT / '.evaluation/business_ocr/references.jsonl').read_text().splitlines()]
    pages = {p['id']: p for p in read(ROOT / '.evaluation/kh_funsd_local/page-selection.json')['pages']}
    expected_business = set()
    for r in refs:
        dims = pages[r['id']]['upright_dimensions']
        letters = sum(0x1780 <= ord(c) <= 0x17D3 and unicodedata.category(c)[0] in ('L', 'M') for c in r['transcript'])
        if not r['uncertain_spans'] and '[ILLEGIBLE]' not in r['transcript'] and letters >= 50 and min(dims) >= 500 and max(dims) >= 1000:
            expected_business.add(r['id'])
    expanded = read(ROOT / '.evaluation/expanded_ocr/prepared.json')
    expected_khob = {u['id'] for g in expanded['groups'] if g['dataset'] == 'khob' and g['source_id'].split('/')[0] == 'task-1' for u in g['units']}
    expected_candidates = {('khob-digital', i) for i in expected_khob} | {('khfunsd-screened', i) for i in expected_business}
    if {(p['track'], p['id']) for p in manifest['candidates']} != expected_candidates:
        raise ValueError('Independent input-only eligibility differs')
    decisions = {(p['track'], p['id']): p['decision'] for p in review['decisions']}
    selected = {(p['track'], p['id']): p for p in frozen['selected_pages']}
    if (set(decisions) != expected_candidates or set(selected) != {k for k, d in decisions.items() if d == 'accept'} or
            review['reviewed_against_predictions'] is not False or review['human_reviewed'] is not False):
        raise ValueError('Visual selection or review claims differ')
    for page in selected.values():
        if digest(Path(page['image'])) != page['image_sha256']:
            raise ValueError('Selected image changed')
        if hashlib.sha256(page['reference'].encode('utf-8')).hexdigest() != page['reference_sha256']:
            raise ValueError('Selected reference changed')
    expected_systems = {'khob-digital': {'tesseract-fast', 'ket-ocr'},
        'khfunsd-screened': {'tesseract-fast', 'khmereasytools-fast', 'surya-2', 'paddleocr-vl-1.6-4bit', 'deepseek-ocr-4bit'}}
    expected_rows = {(track, identity, system) for track, identity in selected for system in expected_systems[track]}
    rows = counts['records']
    actual_rows = [(r['track'], r['id'], r['system']) for r in rows]
    if len(actual_rows) != len(set(actual_rows)) or set(actual_rows) != expected_rows:
        raise ValueError('Incomplete or duplicate matched system coverage')
    needed = {r['raw_sha256'] for r in rows if r['track'] == 'khob-digital'}
    khob_sources = {}
    for path in (ROOT / '.evaluation/expanded_ocr/predictions').glob('*/*.json'):
        sha = digest(path)
        if sha in needed:
            khob_sources[sha] = read(path)
    if set(khob_sources) != needed:
        raise ValueError('Missing original KHOB raw records')
    totals = defaultdict(lambda: defaultdict(Counter))
    flags = defaultdict(Counter)
    backends = {'tesseract-fast': 'cpu', 'khmereasytools-fast': 'cpu', 'surya-2': 'surya',
                'paddleocr-vl-1.6-4bit': 'mlx', 'deepseek-ocr-4bit': 'mlx'}
    for row in rows:
        track, identity, system = row['track'], row['id'], row['system']
        page = selected[track, identity]
        if row['reference_sha256'] != page['reference_sha256']:
            raise ValueError('Scored reference hash differs')
        if track == 'khob-digital':
            raw = khob_sources[row['raw_sha256']]
            predicted = next(p for p in raw['predictions'] if p['id'] == identity and p['variant'] == 'clean')
            scored = next(p for p in raw['rows'] if p['id'] == identity and p['variant'] == 'clean')
            field = 'baseline' if system == 'tesseract-fast' else 'toolkit'
            prediction, error, capped = predicted[field], scored[field]['failed'], None
            if predicted['reference'] != page['reference']:
                raise ValueError('Original KHOB reference differs')
        else:
            backend = backends[system]
            home = ROOT / '.evaluation/business_ocr'
            if backend not in ('cpu', 'surya'):
                home = home / 'server-run' / backend
            filename = hashlib.sha256(identity.encode()).hexdigest() + '.json'
            path = home / 'predictions' / row['evaluation_token'] / system / filename
            if digest(path) != row['raw_sha256']:
                raise ValueError('Original business prediction changed')
            raw = read(path)
            prediction = raw['prediction'] if 'prediction' in raw else visible_text(raw['raw'])
            error, capped = bool(raw['error']), raw.get('capped')
            if raw['image_sha256'] != page['image_sha256']:
                raise ValueError('Raw model input image differs')
        if bool(error) != bool(row['error']) or (not prediction.strip()) != row['empty'] or capped != row['capped']:
            raise ValueError('Failure/empty/cap accounting differs')
        left, right = project(page['reference']), project(prediction)
        key = track, system
        for name in left:
            score = row['scores'][name]
            distance = edit_distance(left[name], right[name])
            if (score['edits'] != distance or score['reference_units'] != len(left[name]) or
                    score['prediction_units'] != len(right[name]) or
                    score['substitutions'] + score['deletions'] + score['insertions'] != distance):
                raise ValueError('Independent edit distance or unit count differs')
            totals[key][name].update({n: score[n] for n in
                ['substitutions', 'deletions', 'insertions', 'reference_units', 'prediction_units', 'edits']})
        flags[key].update(samples=1, errors=bool(error), empty=not prediction.strip(),
                          capped=capped is True, capped_unknown=capped is None,
                          exact_compact_units=left['compact_cer'] == right['compact_cer'])
    for (track, system), metrics in totals.items():
        expected = dict(flags[track, system])
        for name, total in metrics.items():
            expected[name] = dict(total)
            expected[name]['error_rate'] = total['edits'] / total['reference_units'] if total['reference_units'] else None
        if expected != result['summaries'][track][system]:
            raise ValueError('Independent aggregate differs')
    output = dict(passed=True, audit_sha256=digest(Path(__file__)),
        results_sha256=digest(PUBLIC / 'results.json'), selection_sha256=digest(PUBLIC / 'selection.json'),
        candidate_images_screened=len(expected_candidates), selected_image_hashes_verified=len(selected),
        prediction_records_verified=len(rows), independent_distance_projections=3*len(rows),
        aggregate_system_tracks_verified=len(totals), bit_vector_dp_selfchecks=self_check(),
        notes=['Separate input-eligibility and bit-vector distance implementations agree with published selection/counts.',
               'All retained raw outputs, references, images, empty/error/cap flags and aggregate counts checked.',
               'Assistant image screening is not human transcript review; post hoc selection is not an unseen test.'])
    (PUBLIC / 'consistency-audit.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
