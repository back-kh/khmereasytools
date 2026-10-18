"""Audit private Codex drafts and prepare an offline human-review artifact."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".evaluation/kh_funsd_local"
PUBLIC = ROOT / "benchmarks/accuracy/small-vlm/reference-authoring"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


HTML = r'''<!doctype html>
<html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self' data: file:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'">
<title>Khmer document transcript review</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f5f7;color:#17202b;font:15px system-ui,sans-serif}
header{padding:20px 26px;background:white;border-bottom:1px solid #d8dde3}h1{font-size:23px;margin:0 0 8px}p{margin:6px 0;line-height:1.5}
nav{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:14px}button,select,input{font:inherit;padding:9px 12px;border:1px solid #b7c0cc;border-radius:6px;background:white}button{cursor:pointer}button:disabled{opacity:.45;cursor:default}
button.primary{background:#2156a5;color:white;border-color:#2156a5}main{display:grid;grid-template-columns:minmax(0,1fr) minmax(420px,1fr);gap:16px;padding:18px;height:calc(100vh - 205px)}
section{background:white;border:1px solid #d8dde3;border-radius:8px;min-height:0;padding:16px;overflow:auto}.image{background:#e7ebef;text-align:center}.image img{max-width:100%;height:auto;background:white}
.editor{display:flex;flex-direction:column;gap:10px}textarea{resize:vertical;width:100%;min-height:240px;flex:1;padding:12px;font:18px/1.65 'Noto Sans Khmer','Khmer MN',sans-serif;border:1px solid #aab5c4;border-radius:5px;tab-size:4}
.muted{color:#536173;font-size:13px}.status{font-weight:600}.checks label{display:block;margin:9px 0;line-height:1.5}.checks input{padding:0;margin-right:8px}details{border-top:1px solid #e2e6ec;padding-top:10px}ul{padding-left:20px;line-height:1.6}.notice{min-height:20px;color:#8f3323}
@media(max-width:950px){main{display:block;height:auto}section{margin-bottom:16px}.editor{min-height:650px}}
</style>
<header><h1>Khmer document transcript review</h1>
<p>These are model-generated drafts. Check every visible character and the reading order against the image before approving a complete reference.</p>
<nav><button id="prev">Previous</button><select id="pages" aria-label="Document"></select><button id="next">Next</button><span id="progress" class="status"></span>
<input id="reviewer" aria-label="Reviewer name" placeholder="Reviewer name"><button id="exportAll">Export all drafts and reviews</button><button id="exportReviewed" class="primary">Export complete reviewed references</button></nav>
<p class="muted">Edits stay in this browser. Export a backup when you finish reviewing. Existing edits are preserved when the same source image is opened again.</p></header>
<main><section class="image"><p><a id="fullImage" target="_blank" rel="noopener">Open original image at full size</a></p><img id="image" alt="Source document"></section>
<section class="editor"><div><strong id="label"></strong><p id="identity" class="muted"></p></div>
<textarea id="text" aria-label="Transcript"></textarea><div class="checks">
<label><input type="checkbox" id="reviewed">I reviewed the text and reading order against the source image</label>
<label><input type="checkbox" id="complete">All visible text is transcribed and no unresolved span remains</label></div>
<div id="notice" class="notice" role="status"></div><details><summary>Model uncertainty notes</summary><ul id="uncertainty"></ul></details>
<p class="muted">A model's complete flag does not approve a reference. Both checks above require a human decision. Unresolved [ILLEGIBLE] markers prevent complete-reference export.</p></section></main>
<script id="data" type="application/json">__DATA__</script>
<script>
'use strict';
const payload=JSON.parse(document.getElementById('data').textContent), rows=payload.pages;
const namespace='khmereasytools-khfunsd-review-v1:', sessionReviews=new Map();let index=0;
const $=id=>document.getElementById(id);
function stored(row){if(sessionReviews.has(row.id))return sessionReviews.get(row.id);try{const s=JSON.parse(localStorage.getItem(namespace+row.id));return s&&typeof s.transcript==='string'&&s.source_image_sha256===row.image_sha256?s:null}catch{return null}}
function state(row){return stored(row)||{transcript:row.transcript,human_reviewed:false,reference_complete:false,reviewer:null,reviewed_at:null,source_image_sha256:row.image_sha256}}
function approved(s){return s.human_reviewed===true&&s.reference_complete===true&&typeof s.reviewer==='string'&&s.reviewer.trim()&&!s.transcript.includes('[ILLEGIBLE]')}
function refresh(){let n=0;for(const row of rows){if(approved(state(row)))n++}$('progress').textContent=n+' / '+rows.length+' complete reviewed references';$('exportReviewed').disabled=n===0}
function save(){const row=rows[index],name=$('reviewer').value.trim();let checked=$('reviewed').checked,complete=$('complete').checked,warning='';
 if((checked||complete)&&!name){warning='Enter the reviewer name before marking a review. Text edits are saved as a draft.';checked=false;complete=false;$('reviewed').checked=false;$('complete').checked=false}
 if(complete&&(!checked||$('text').value.includes('[ILLEGIBLE]'))){warning='Complete references need human review and no [ILLEGIBLE] marker. Text edits are saved.';complete=false;$('complete').checked=false}
 const value={transcript:$('text').value,human_reviewed:checked,reference_complete:checked&&complete,reviewer:checked?name:null,reviewed_at:checked?new Date().toISOString():null,source_image_sha256:row.image_sha256};
 sessionReviews.set(row.id,value);
 try{localStorage.setItem(namespace+row.id,JSON.stringify(value));localStorage.setItem(namespace+'reviewer',name);$('notice').textContent=warning||'Saved in this browser.'}catch{$('notice').textContent='Browser storage is unavailable. Export the current review before closing.'}refresh()}
function show(){const row=rows[index],s=state(row);$('pages').value=String(index);$('label').textContent=(index+1)+' / '+rows.length+' · '+row.category+' · '+row.acquisition_folder;$('identity').textContent=row.id;
 $('image').src=row.image;$('fullImage').href=row.image;$('text').value=s.transcript;$('reviewed').checked=s.human_reviewed;$('complete').checked=s.reference_complete;$('prev').disabled=index===0;$('next').disabled=index===rows.length-1;$('notice').textContent='';
 $('uncertainty').replaceChildren();for(const item of row.uncertain_spans){const li=document.createElement('li');li.textContent=item.text+' — '+item.reason;$('uncertainty').appendChild(li)}refresh()}
function exported(row){const s=state(row);return {id:row.id,source_image_sha256:row.image_sha256,source_byte_sha256:row.source_sha256,transcript:s.transcript,human_reviewed:s.human_reviewed,reference_complete:s.reference_complete,reviewer:s.reviewer,reviewed_at:s.reviewed_at,original_model_draft_sha256:row.draft_sha256,draft_token:payload.draft_token}}
function download(completeOnly){const selected=rows.map(exported).filter(x=>!completeOnly||approved(x));const text=selected.map(x=>JSON.stringify(x)).join('\n')+'\n';const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([text],{type:'application/x-ndjson;charset=utf-8'}));link.download=completeOnly?'khmer-reviewed-complete-references.jsonl':'khmer-transcript-drafts-and-reviews.jsonl';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)}
rows.forEach((r,i)=>{const option=document.createElement('option');option.value=String(i);option.textContent=(i+1)+' · '+r.category+' · '+r.id;$('pages').appendChild(option)});
try{$('reviewer').value=localStorage.getItem(namespace+'reviewer')||''}catch{}
$('text').addEventListener('input',()=>{$('complete').checked=false;save()});$('reviewed').addEventListener('change',()=>{if(!$('reviewed').checked)$('complete').checked=false;save()});$('complete').addEventListener('change',save);$('reviewer').addEventListener('change',save);
$('pages').addEventListener('change',()=>{index=Number($('pages').value);show()});$('prev').addEventListener('click',()=>{index--;show()});$('next').addEventListener('click',()=>{index++;show()});$('exportAll').addEventListener('click',()=>download(false));$('exportReviewed').addEventListener('click',()=>download(true));show();
</script></html>'''


def main():
    profile = read(DATA / "draft-protocol.json")
    selection = read(DATA / "page-selection.json")
    if len(selection["pages"]) != 146 or digest(DATA / "page-selection.json") != profile["source_selection_sha256"]:
        raise ValueError("Source inventory changed")
    if digest(ROOT / "scripts/draft_khfunsd_codex.py") != profile["runner_sha256"]:
        raise ValueError("Reference authoring source differs")
    directory = DATA / "codex-drafts" / profile["token"]
    records, review_rows = [], []
    for page in selection["pages"]:
        path = directory / (page["id"] + ".json")
        if not path.exists():
            raise ValueError("Draft not complete: " + page["id"])
        row = read(path)
        if row["error"] or row["draft_token"] != profile["token"] or row["human_reviewed"]:
            raise ValueError("Draft failed or provenance differs: " + page["id"])
        if row["image_sha256"] != page["image_sha256"] or digest(DATA / page["image"]) != page["image_sha256"]:
            raise ValueError("Input image differs")
        if row["generation_overrides"] != profile["generation_overrides"] or row["runner_sha256"] != profile["runner_sha256"]:
            raise ValueError("Annotation settings differ")
        events_path = directory / (page["id"] + ".events.jsonl")
        if digest(events_path) != row["events_sha256"]:
            raise ValueError("Annotation event log differs")
        events = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
        if any(e.get("type") == "item.completed" and e["item"]["type"] not in {"agent_message", "reasoning"} for e in events):
            raise ValueError("Image-only annotation used tools")
        draft = row["draft"]
        if draft["page_id"] != page["id"]:
            raise ValueError("Model returned the wrong page identity")
        records.append(row)
        review_rows.append(dict(id=page["id"], image=page["image"],
            image_sha256=page["image_sha256"], source_sha256=page["source_sha256"],
            category=page["category"], acquisition_folder=page["acquisition_folder"],
            transcript=draft["transcript"], uncertain_spans=draft["uncertain_spans"],
            draft_sha256=hashlib.sha256(draft["transcript"].encode()).hexdigest(),
            human_reviewed=False, reference_complete=False))
    summary = dict(raw_image_files=148, selected_distinct_images=146,
        completed_drafts=len(records), failed_calls=0, human_reviewed=0,
        uncertain_pages=sum(bool(r["draft"]["uncertain_spans"]) for r in records),
        illegible_pages=sum("[ILLEGIBLE]" in r["draft"]["transcript"] for r in records),
        model_claimed_complete_pages=sum(r["draft"]["complete"] for r in records),
        generated_transcript_codepoints=sum(len(r["draft"]["transcript"]) for r in records),
        draft_token=profile["token"], configured_model=profile["configured_model"],
        generation_overrides=profile["generation_overrides"], cli_version=profile["cli_version"],
        resolved_model_snapshot=profile["resolved_model_snapshot"],
        compiler_sha256=digest(Path(__file__)),
        interpretation="Reference-authoring drafts only; no independent gold or OCR accuracy claim")
    PUBLIC.mkdir(parents=True, exist_ok=True)
    (PUBLIC / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    output = DATA / "reference-drafts.jsonl"
    output.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in review_rows), encoding="utf-8")
    payload = json.dumps(dict(draft_token=profile["token"], pages=review_rows), ensure_ascii=False).replace("<", "\\u003c")
    (DATA / "review.html").write_text(HTML.replace("__DATA__", payload), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("Private reference drafts and offline review page saved on", DATA.resolve())


if __name__ == "__main__":
    main()
