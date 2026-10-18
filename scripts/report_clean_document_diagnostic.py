"""Freeze input-only selection, then subset previously audited OCR counts."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from ocr_word_metrics import aggregate

DATA = ROOT / '.evaluation/clean_document_diagnostic'
PUBLIC = ROOT / 'benchmarks/accuracy/clean-document-diagnostic'
METRICS = ('compact_cer', 'whitespace_unit_wer', 'segmentation_assisted_wer')
SYSTEMS = {
    'khob-digital': ('tesseract-fast', 'ket-ocr'),
    'khfunsd-screened': ('tesseract-fast', 'khmereasytools-fast', 'surya-2',
                         'paddleocr-vl-1.6-4bit', 'deepseek-ocr-4bit')}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def token(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def freeze_selection():
    manifest_path, review_path = DATA / 'candidate-manifest.json', DATA / 'visual-screen.json'
    manifest, review = read(manifest_path), read(review_path)
    payload = {k: v for k, v in manifest.items() if k != 'selection_token'}
    if token(payload) != manifest['selection_token']:
        raise ValueError('Candidate selection token differs')
    if manifest['selection_reads_predictions'] is not False:
        raise ValueError('Selection cannot use OCR predictions')
    for name, expected in manifest['sources'].items():
        if digest(ROOT / name) != expected:
            raise ValueError('Frozen selection source changed: ' + name)
    if review['selection_token'] != manifest['selection_token'] or review['reviewed_against_predictions'] is not False:
        raise ValueError('Visual screen identity or blinding differs')
    if review.get('human_reviewed') is not False or review.get('reference_complete') is not False:
        raise ValueError('Do not promote this assistant image screen to human reference verification')
    candidates = {(p['track'], p['id']): p for p in manifest['candidates']}
    decisions = {(p['track'], p['id']): p for p in review['decisions']}
    if len(decisions) != len(review['decisions']) or set(candidates) != set(decisions):
        raise ValueError('Visual decisions must cover every candidate exactly once')
    for key, decision in decisions.items():
        if decision['decision'] not in ('accept', 'reject') or not decision['reason'].strip():
            raise ValueError('Unfinished or unexplained visual decision: ' + repr(key))
    selected = [p for p in manifest['candidates'] if decisions[p['track'], p['id']]['decision'] == 'accept']
    if not all(any(p['track'] == track for p in selected) for track in SYSTEMS):
        raise ValueError('A selected track is empty')
    path = DATA / 'final-selection.json'
    identities = dict(candidate_manifest_sha256=digest(manifest_path),
                      visual_screen_sha256=digest(review_path))
    if path.exists():
        frozen = read(path)
        if any(frozen.get(k) != v for k, v in identities.items()) or frozen['selected_pages'] != selected:
            raise ValueError('Preserve final frozen selection; inputs or decisions changed')
        if token({k: v for k, v in frozen.items() if k != 'freeze_token'}) != frozen['freeze_token']:
            raise ValueError('Final selection token differs')
        return frozen
    frozen = dict(schema_version=1, frozen_utc=datetime.now(timezone.utc).isoformat(),
        **identities, candidate_selection_token=manifest['selection_token'],
        design=manifest['design'], selected_pages=selected,
        candidates_by_track=manifest['eligible_by_track'],
        selected_by_track=dict(Counter(p['track'] for p in selected)),
        visual_decisions=review['decisions'], metadata_exclusions=manifest['exclusions'],
        prediction_access_for_selection=False, new_human_reference_reviews=0)
    frozen['freeze_token'] = token(frozen)
    write(path, frozen)
    safe = dict(frozen)
    safe['selected_pages'] = [{k: v for k, v in p.items() if k not in ('image', 'reference')}
                              for p in selected]
    safe['private_final_selection_sha256'] = digest(path)
    write(PUBLIC / 'selection.json', safe)
    return frozen


def validate_counts(row):
    for name in METRICS:
        score = row['scores'][name]
        numbers = ['substitutions', 'deletions', 'insertions', 'reference_units', 'prediction_units', 'edits']
        if any(type(score[n]) is not int or score[n] < 0 for n in numbers):
            raise ValueError('Invalid edit counts')
        s, d, i = (score[n] for n in numbers[:3])
        r, p = score['reference_units'], score['prediction_units']
        if s + d + i != score['edits'] or p - r != i - d or s + d > r or s + i > p:
            raise ValueError('Edit count algebra differs')
        expected = score['edits'] / r if r else None
        if score['error_rate'] != expected:
            raise ValueError('Error ratio differs')


def score_selection(frozen):
    # No prediction/count file is opened before final-selection.json exists.
    output_path = PUBLIC / 'results.json'
    if output_path.exists():
        raise ValueError('Preserve published diagnostic results; scoring is one-time')
    word_public_path = ROOT / 'benchmarks/accuracy/ocr-word-errors/results.json'
    business_public_path = ROOT / 'benchmarks/accuracy/business-ocr/results.json'
    business_audit_path = business_public_path.with_name('consistency-audit.json')
    word_private_path = ROOT / '.evaluation/ocr_word_errors/results-with-count-records.json'
    business_private_path = ROOT / '.evaluation/business_ocr/scored-count-records.json'
    word_public, business_audit = read(word_public_path), read(business_audit_path)
    if (not word_public['independent_audit']['passed'] or not business_audit['passed'] or
            word_public['private_count_records_sha256'] != digest(word_private_path) or
            business_audit['private_count_records_sha256'] != digest(business_private_path) or
            business_audit['results_sha256'] != digest(business_public_path)):
        raise ValueError('Previously audited count-file identities differ')
    inputs = {'khob-digital': read(word_private_path), 'khfunsd-screened': read(business_private_path)}
    accepted = {(p['track'], p['id']): p for p in frozen['selected_pages']}
    grouped, rows = defaultdict(list), []
    for track, data in inputs.items():
        for row in data['records']:
            key = (track, row['id'])
            if key not in accepted or row['system'] not in SYSTEMS[track]:
                continue
            if track == 'khob-digital' and row['collection'] != 'khob_clean':
                continue
            if row['reference_sha256'] != accepted[key]['reference_sha256']:
                raise ValueError('Selected reference differs from audited reference')
            validate_counts(row)
            copy = dict(row, track=track)
            rows.append(copy)
            grouped[track, row['system']].append(copy)
    expected = {(p['track'], p['id'], system) for p in frozen['selected_pages'] for system in SYSTEMS[p['track']]}
    actual = [(r['track'], r['id'], r['system']) for r in rows]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError('Matched selected-track coverage differs')
    summary = {}
    for (track, system), selected in sorted(grouped.items()):
        value = {name: aggregate([r['scores'][name] for r in selected]) for name in METRICS}
        value.update(samples=len(selected), empty=sum(r['empty'] for r in selected),
                     errors=sum(bool(r['error']) for r in selected),
                     capped=sum(r['capped'] is True for r in selected),
                     capped_unknown=sum(r['capped'] is None for r in selected),
                     exact_compact_units=sum(r['scores']['compact_cer']['edits'] == 0 for r in selected))
        summary.setdefault(track, {})[system] = value
    counts_path = DATA / 'selected-audited-counts.json'
    write(counts_path, dict(freeze_token=frozen['freeze_token'], records=rows))
    result = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
        analysis_sha256=digest(Path(__file__)), freeze_token=frozen['freeze_token'],
        selection_sha256=digest(PUBLIC / 'selection.json'),
        private_selected_count_records_sha256=digest(counts_path),
        source_hashes={str(p.relative_to(ROOT)): digest(p) for p in
            [word_public_path, business_public_path, business_audit_path, word_private_path, business_private_path]},
        selected_by_track=frozen['selected_by_track'], record_count=len(rows),
        reference_review='Zero new independent human reviews; original references unchanged',
        summaries=summary,
        source_distance_audits_reused=True,
        source_audit_projections=dict(word=word_public['independent_audit']['independently_checked_projections'],
                                     business=business_audit['independent_projections_verified']),
        notes=['Post hoc focused diagnostic after larger results were known; not an unseen test set.',
               'Selection used source quality and reference flags, with no per-image OCR scores.',
               'Reuses unchanged prior predictions and independently audited edit counts; no new inference.',
               'Selected tracks are separate and must not be pooled.',
               'All selected-system outputs retained, including empty, capped and failed calls.',
               'KH-FUNSD references remain unreviewed machine-generated operational ground truth.',
               'Digital exports may retain fine print, stamps and handwritten administrative fields.',
               'Qwen is excluded because its earlier matched30 selection does not cover this complete track.',
               'No guarantee that input screening lowers CER or establishes real-world accuracy.'])
    write(output_path, result)
    print(json.dumps(dict(selected_by_track=frozen['selected_by_track'], record_count=len(rows),
        results=str(output_path), cer_percent={track: {name: round(100*v['compact_cer']['error_rate'], 4)
                       for name, v in systems.items()} for track, systems in summary.items()}), indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--freeze-only', action='store_true')
    args = parser.parse_args()
    frozen = freeze_selection()
    if args.freeze_only:
        print(json.dumps(dict(freeze_token=frozen['freeze_token'], selected_by_track=frozen['selected_by_track']), indent=2))
        return
    score_selection(frozen)


if __name__ == '__main__':
    main()
