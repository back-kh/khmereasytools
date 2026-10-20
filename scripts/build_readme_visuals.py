"""Build documentation artwork from existing checked-in results; no new evaluation.

Optional authoring dependencies only. This script is never imported by the
runtime package. Khmer glyphs are shaped with HarfBuzz and drawn as outlines;
no font file, external corpus, model download or network call is included.
"""

import argparse
import ast
import hashlib
import inspect
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fontTools
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, PathPatch, Rectangle
from matplotlib.path import Path as MPath
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
import uharfbuzz as hb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import khmereasytools as ket

NAVY = "#102B3C"
TEAL = "#007D73"
MINT = "#DDF1E8"
CREAM = "#FAF8F1"
BLUE = "#E6EFF6"
INK = "#173447"
GRAY = "#526573"
LIGHT = "#DEE5E7"
ORANGE = "#A84D25"
PEACH = "#FAEADF"
WHITE = "#FFFFFF"
BASELINE = "#9DAEB6"

plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "path",
                     "svg.hashsalt": "khmereasytools-readme-v05",
                     "pdf.fonttype": 42, "axes.unicode_minus": False})


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class GlyphPen(BasePen):
    def __init__(self, glyphs):
        super().__init__(glyphs)
        self.vertices, self.codes = [], []

    def _moveTo(self, p):
        self.vertices.append(p); self.codes.append(MPath.MOVETO)

    def _lineTo(self, p):
        self.vertices.append(p); self.codes.append(MPath.LINETO)

    def _curveToOne(self, p1, p2, p3):
        self.vertices.extend((p1, p2, p3)); self.codes.extend((MPath.CURVE4,) * 3)

    def _qCurveToOne(self, p1, p2):
        self.vertices.extend((p1, p2)); self.codes.extend((MPath.CURVE3,) * 2)

    def _closePath(self):
        self.vertices.append((0, 0)); self.codes.append(MPath.CLOSEPOLY)

    def _endPath(self):
        pass


class KhmerOutlines:
    def __init__(self, path):
        self.path = Path(path)
        self.tt = TTFont(str(path))
        if self.tt["OS/2"].fsType & 2:
            raise ValueError("Use a Khmer font that permits embedding")
        self.glyphs = self.tt.getGlyphSet()
        self.font = hb.Font(hb.Face(self.path.read_bytes()))
        self.units = self.tt["head"].unitsPerEm
        self.font.scale = (self.units, self.units)
        self.cache = {}

    def draw(self, board, x, baseline, text, size, color=INK):
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.font, buffer)
        cursor_x = cursor_y = 0
        for info, position in zip(buffer.glyph_infos, buffer.glyph_positions):
            name = self.tt.getGlyphName(info.codepoint)
            if name not in self.cache:
                pen = GlyphPen(self.glyphs)
                self.glyphs[name].draw(pen)
                self.cache[name] = (pen.vertices, pen.codes)
            vertices, codes = self.cache[name]
            if vertices:
                points = [(x + (px + cursor_x + position.x_offset) * size / self.units,
                           baseline - (py + cursor_y + position.y_offset) * size / self.units)
                          for px, py in vertices]
                board.ax.add_patch(PathPatch(MPath(points, codes), facecolor=color,
                                             edgecolor="none", zorder=5))
            cursor_x += position.x_advance
            cursor_y += position.y_advance
        return cursor_x * size / self.units


class Board:
    def __init__(self, width, height, *, background=CREAM, a3=False):
        self.width, self.height = width, height
        self.dpi = width / (297 / 25.4) if a3 else 100
        self.fig = plt.figure(figsize=(width / self.dpi, height / self.dpi), dpi=self.dpi,
                              facecolor=background)
        self.ax = self.fig.add_axes([0, 0, 1, 1], xlim=(0, width), ylim=(height, 0))
        self.ax.axis("off")

    def text(self, x, y, value, size=24, *, color=INK, weight="normal", mono=False, **kwargs):
        return self.ax.text(x, y, value, fontsize=size * 72 / self.dpi, color=color,
                            weight=weight, fontfamily="DejaVu Sans Mono" if mono else "DejaVu Sans",
                            va="top", linespacing=1.42, zorder=6, **kwargs)

    def box(self, x, y, width, height, *, fill=WHITE, edge="none", radius=16, lw=1):
        patch = FancyBboxPatch((x, y), width, height,
                              boxstyle="round,pad=0,rounding_size={}".format(radius),
                              linewidth=lw, edgecolor=edge, facecolor=fill, zorder=2)
        self.ax.add_patch(patch)

    def line(self, x1, y1, x2, y2, color=LIGHT, lw=1.5, **kwargs):
        self.ax.plot([x1, x2], [y1, y2], color=color, linewidth=lw, zorder=3, **kwargs)

    def arrow(self, x1, y1, x2, y2, color=TEAL, *, dashed=False):
        self.ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                         mutation_scale=20, linewidth=2.4, color=color,
                                         linestyle="--" if dashed else "-", zorder=4))

    def save(self, base, title, *, date, pdf=False, svg=True):
        # Text extents catch clipped headings/labels before accepting artwork.
        self.fig.canvas.draw()
        renderer = self.fig.canvas.get_renderer()
        for text in self.ax.texts:
            extent = text.get_window_extent(renderer)
            if (extent.x0 < -1 or extent.y0 < -1 or extent.x1 > self.width + 1 or
                    extent.y1 > self.height + 1):
                raise ValueError("Artwork text leaves canvas: " + text.get_text())
        self.fig.savefig(str(base) + ".png", dpi=self.dpi, facecolor=self.fig.get_facecolor(),
                         metadata={"Title": title, "Description": "KhmerEasyTools source 0.5.0.dev0; existing evidence only."})
        if svg:
            self.fig.savefig(str(base) + ".svg", facecolor=self.fig.get_facecolor(),
                             metadata={"Title": title, "Date": date, "Creator": "KhmerEasyTools"})
        if pdf:
            created = datetime.fromisoformat(date).replace(tzinfo=timezone(timedelta(hours=8)))
            self.fig.savefig(str(base) + ".pdf", facecolor=self.fig.get_facecolor(),
                             metadata={"Title": title, "Author": "Nimol Thuon",
                                       "Subject": "Technical overview of KhmerEasyTools 0.5.0 development source",
                                       "CreationDate": created, "ModDate": created})
        plt.close(self.fig)


def evidence():
    sources = {}
    def read(name):
        sources[name] = digest(ROOT / name)
        return json.loads((ROOT / name).read_text(encoding="utf-8"))
    before = read("benchmarks/accuracy/improvements/baseline_reserved.json")
    after = read("benchmarks/accuracy/improvements/improved_reserved.json")
    tagger = read("benchmarks/accuracy/tagger-v2/results.json")
    dictionary = read("khmereasytools/data/dictionary_manifest.json")
    model = read("khmereasytools/data/research/manifest.json")
    validation = read("benchmarks/accuracy/tagger-v2/native-validation.json")
    assert digest(ROOT / "khmereasytools/data/research/ket_pos_v2.json.gz") == model["sha256"]
    runtime = hashlib.sha256()
    for path in sorted((ROOT / "khmereasytools").rglob("*.py")):
        runtime.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        runtime.update(path.read_bytes())
    assert runtime.hexdigest() == tagger["metadata"]["runtime_python_sources_sha256"]
    setup = ROOT / "setup.py"
    sources["setup.py"] = digest(setup)
    calls = [node for node in ast.walk(ast.parse(setup.read_text(encoding="utf-8")))
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "setup"]
    assert len(calls) == 1
    requirements = next(value.value for value in calls[0].keywords if value.arg == "install_requires")
    assert ast.literal_eval(requirements) == []
    for field in ("khpos_segmentation", "alt_words"):
        assert before[field]["sentences"] == after[field]["sentences"]
        assert before[field]["gold_tokens"] == after[field]["gold_tokens"]
    assert before["ocr"]["public_default"]["samples"] == after["ocr"]["public_default"]["samples"] == 40
    core = [r for r in validation["records"] if "tests" in r and not r["real_ocr"]]
    extras = [r for r in validation["records"] if r.get("real_ocr")]
    assert len(core) == len(extras) == 3
    assert all(r["tests"] == 222 and r["failures"] == r["errors"] == 0 for r in core + extras)
    metrics = dict(
        segmentation=[before["khpos_segmentation"]["metrics"]["segmentation"]["f1"] * 100,
                      after["khpos_segmentation"]["metrics"]["segmentation"]["f1"] * 100],
        coarse_pos=[tagger["alt"]["rules"]["gold_boundaries"]["all_token_coarse_accuracy"] * 100,
                    tagger["alt"]["compact"]["gold_boundaries"]["all_token_coarse_accuracy"] * 100],
        ocr_cer=[before["ocr"]["public_default"]["compact_codepoint_cer"] * 100,
                 after["ocr"]["public_default"]["compact_codepoint_cer"] * 100],
        native_pos=tagger["close"]["native_23_labels"]["native_accuracy"] * 100,
        native_joint=tagger["close"]["native_23_labels"]["joint_native"]["f1"] * 100,
        public_pos=tagger["close"]["compact_public"]["gold_boundaries"]["all_token_mapped_upos_accuracy"] * 100,
        public_joint=tagger["close"]["compact_public"]["reconstructed_text"]["joint_mapped_upos"]["f1"] * 100,
        dictionary_entries=dictionary["combined_entries"], model_bytes=model["bytes"],
        api_functions=sum(inspect.isfunction(getattr(ket, name)) for name in ket.__all__),
        core_passed=core[0]["tests"] - core[0]["skipped"], core_skipped=core[0]["skipped"],
        extras_passed=extras[0]["tests"] - extras[0]["skipped"], extras_skipped=extras[0]["skipped"],
    )
    return metrics, sources


def hero(output, metrics, khmer, date):
    b = Board(1600, 500, background=NAVY)
    b.text(65, 38, "KHMER EASY TOOLS  /  0.5 DEVELOPMENT", 22, color="#98D5C0", weight="bold")
    b.text(62, 101, "Everyday Khmer.", 78, color=WHITE, weight="bold")
    b.text(65, 204, "Text, documents and useful answers - with a small local core.", 28, color="#DCE7EB")
    khmer.draw(b, 66, 308, "ឧបករណ៍ភាសាខ្មែរ", 49, color="#98D5C0")
    b.line(65, 353, 1535, 353, color="#45616E")
    labels = [("{:,}".format(metrics["dictionary_entries"]), "dictionary entries"),
              ("{:.0f} KiB".format(metrics["model_bytes"] / 1024), "bundled POS model"),
              ("0", "core runtime dependencies"), ("3 OS", "native installation checks")]
    for x, (value, label) in zip((65, 430, 795, 1160), labels):
        b.text(x, 377, value, 40, color=WHITE, weight="bold")
        b.text(x, 439, label, 19, color="#C2D4DD")
    b.save(output / "overview", "KhmerEasyTools: everyday Khmer tools", date=date)


def architecture(output, date):
    b = Board(1600, 1040)
    b.text(65, 42, "How the toolkit fits together", 44, weight="bold")
    b.text(65, 111, "Core text tools run locally. Optional backends are explicit, separate choices.", 25, color=GRAY)
    # Each row is an execution path, with an explicit OCR-to-core connection.
    b.box(55, 180, 1490, 290, fill=MINT)
    b.text(82, 201, "LOCAL CORE  /  STANDARD LIBRARY", 21, color=TEAL, weight="bold")
    b.box(85, 252, 285, 170)
    b.text(108, 276, "Text and files", 29, weight="bold")
    b.text(108, 332, "UTF-8 text\nPython API or CLI", 23, color=GRAY)
    b.arrow(377, 338, 448, 338)
    b.box(455, 252, 650, 170)
    b.text(480, 275, "Prepare, segment, tag and retrieve", 28, weight="bold")
    b.text(480, 328, "Audit + normalize  |  khseg + khtag\nSentences + extraction  |  BM25 + KhmerRAG", 23, color=GRAY)
    b.arrow(1112, 338, 1173, 338)
    b.box(1180, 252, 330, 170)
    b.text(1202, 275, "Traceable results", 27, weight="bold")
    b.text(1202, 328, "Words, POS and spans\nPatterns and passages", 23, color=GRAY)

    b.box(55, 540, 1490, 225, fill=BLUE)
    b.text(82, 559, "OPTIONAL OCR  /  ONE-TIME ENGINE + LANGUAGE SETUP", 21, color="#255D81", weight="bold")
    b.box(85, 607, 285, 120)
    b.text(108, 625, "Images and PDFs", 27, weight="bold")
    b.text(108, 673, "Scans and phone images", 20, color=GRAY)
    b.arrow(377, 666, 448, 666, color="#255D81")
    b.box(455, 607, 650, 120)
    b.text(480, 625, "KET-OCR: preparation + Tesseract", 28, weight="bold")
    b.text(480, 677, "Pillow + pytesseract + PDFium  |  khm / khm+eng", 22, color=GRAY)
    b.arrow(1112, 666, 1173, 666, color="#255D81")
    b.box(1180, 607, 330, 120)
    b.text(1202, 625, "Text and geometry", 27, weight="bold")
    b.text(1202, 674, "Words, lines and boxes", 21, color=GRAY)
    b.arrow(780, 539, 780, 472, color="#255D81")
    b.text(810, 488, "OCR text can enter the core workflow", 21, color="#255D81")

    b.box(55, 829, 1490, 150, fill=PEACH)
    b.text(82, 848, "OPTIONAL TRANSLATION / ANSWER GENERATION", 21, color=ORANGE, weight="bold")
    b.text(85, 897, "Explicit client setup", 26, weight="bold")
    b.arrow(397, 916, 448, 916, color=ORANGE, dashed=True)
    b.text(475, 894, "Translation: Google or a local model", 25, weight="bold")
    b.text(475, 936, "RAG answers: a configured generator. Model weights are installed separately.", 21, color=GRAY)
    b.text(1195, 898, "Text / generated answer", 23, weight="bold")
    b.save(output / "architecture", "KhmerEasyTools architecture and optional backends", date=date)


def workflow(output, khmer, date):
    text = "ខ្ញុំអានសៀវភៅ។"
    tokens = ket.khtag(text, with_spans=True)
    assert [(t.text, t.tag) for t in tokens] == [("ខ្ញុំ", "PRON"), ("អាន", "VERB"),
                                               ("សៀវភៅ", "NOUN"), ("។", "PUNCT")]
    b = Board(1600, 785)
    b.text(65, 42, "A tagging result you can inspect", 44, weight="bold")
    b.text(65, 108, "Actual bundled-model output for a documented example; this is not an accuracy test.", 25, color=GRAY)
    b.box(65, 174, 1470, 150, fill=NAVY)
    b.text(95, 196, "ORIGINAL TEXT", 18, color="#98D5C0", weight="bold")
    khmer.draw(b, 95, 285, text, 56, color=WHITE)
    b.text(850, 228, 'khtag(text, with_spans=True)', 26, color=WHITE, mono=True)
    b.arrow(800, 331, 800, 389)
    x_positions = (65, 440, 815, 1190)
    for x, token in zip(x_positions, tokens):
        assert token.text == text[token.start:token.end]
        b.box(x, 407, 345, 228, fill=WHITE, edge=LIGHT)
        b.text(x + 23, 429, token.tag, 26, color=TEAL, weight="bold")
        khmer.draw(b, x + 23, 512, token.text, 43)
        b.line(x + 22, 558, x + 322, 558)
        b.text(x + 23, 580, "source [{}:{})".format(token.start, token.end), 23, color=GRAY, mono=True)
    b.text(65, 675, "Offsets are Python code points, with exclusive ends. Returned token text matches the source.", 25)
    b.text(65, 722, "POS is predicted; role hints are heuristic. No calibrated confidence or automatic spelling correction.", 23, color=GRAY)
    b.save(output / "tagging-workflow", "Actual Khmer tagging example with original-text spans", date=date)
    return dict(text=text, tokens=[dict(t._asdict()) for t in tokens])


def comparisons(output, metrics, date):
    b = Board(1800, 840, background=WHITE)
    b.text(65, 34, "Recorded comparisons, with separate evaluation scopes", 37, weight="bold")
    b.text(65, 99, "Existing fixed results only. Higher is better for F1/accuracy; lower is better for CER.", 24, color=GRAY)
    columns = [
        ("Word segmentation", "Exact-token F1 (%)", metrics["segmentation"], ["Earlier coverage", "Frequency costs"], 100,
         "khPOS OPEN: 1,000 sentences\n10,778 tokens; previously observed."),
        ("KET-Tagger", "Coarse POS accuracy (%)", metrics["coarse_pos"], ["V1 authored rules", "V2 compact model"], 100,
         "ALT: 1,018 sentences / 26,551 words\nGold boundaries; lossy 7-class mapping."),
        ("Printed-page OCR", "Code-point CER (%)", metrics["ocr_cer"], ["Earlier default", "Auto preprocessing"], 20,
         "KHOB: 40 images, 10 documents x 4 variants\nSame Khmer model; local paired comparison."),
    ]
    for index, (title, ylabel, values, labels, maximum, sample) in enumerate(columns):
        left = 85 + index * 585
        b.text(left, 165, title, 31, weight="bold")
        b.text(left, 214, ylabel, 23, color=GRAY)
        ax = b.fig.add_axes([(left + 15) / 1800, 0.30, 440 / 1800, 325 / 840])
        ax.bar([0, 1], values, width=0.53, color=[BASELINE, TEAL if index != 2 else "#307A9A"], zorder=3)
        ax.set_ylim(0, maximum)
        ax.set_xlim(-0.6, 1.6)
        ax.set_xticks([0, 1], labels, fontsize=12)
        ax.set_yticks(range(0, maximum + 1, 20 if maximum == 100 else 5))
        ax.tick_params(axis="y", labelsize=12, length=0, pad=8, colors=GRAY)
        ax.tick_params(axis="x", length=0, pad=14, colors=INK)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.grid(axis="y", color=LIGHT, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for position, value in enumerate(values):
            ax.text(position, value + maximum * 0.025, "{:.2f}".format(value),
                    ha="center", fontsize=18, weight="bold", color=INK)
        b.text(left, 665, sample, 20, color=GRAY)
        if index < 2:
            b.line(left + 515, 165, left + 515, 738)
    b.text(65, 780, "No significance claim. Corpus overlap, annotation conventions and OCR reference/reading-order limits remain.", 23, color=GRAY)
    b.save(output / "evaluation", "Fixed segmentation, coarse POS and OCR comparisons", date=date)


def poster(output, metrics, khmer, date):
    b = Board(1400, 1400 * 420 / 297, a3=True)
    b.ax.add_patch(Rectangle((0, 0), 1400, 370, facecolor=NAVY, edgecolor="none"))
    b.text(65, 36, "TECHNICAL OVERVIEW  /  0.5.0 DEVELOPMENT SOURCE", 22, color="#98D5C0", weight="bold")
    b.text(60, 98, "Khmer Easy Tools", 79, color=WHITE, weight="bold")
    khmer.draw(b, 65, 259, "ឧបករណ៍ភាសាខ្មែរ", 49, color="#98D5C0")
    b.text(65, 296, "Prepare text. Tag words. Search locally. Read documents.", 29, color=WHITE)
    for x, value, label in ((65, "{:,}".format(metrics["dictionary_entries"]), "dictionary entries"),
                            (510, "{:.0f} KiB".format(metrics["model_bytes"] / 1024), "bundled research POS model"),
                            (970, "0", "core runtime dependencies")):
        b.text(x, 412, value, 48, weight="bold")
        b.text(x, 482, label, 22, color=GRAY)
    b.line(65, 540, 1335, 540)
    b.text(65, 572, "01  Everyday tools", 31, color=TEAL, weight="bold")
    for x, heading, body in (
            (65, "Text preparation", "Audit + reversible cleanup\nDigits + lossless source spans\nSentences + pattern extraction"),
            (510, "Words and retrieval", "Segmentation + Khmer POS\nLocal BM25 keyword search\nPassages with source citations"),
            (970, "Documents and setup", "Image / PDF OCR\nLines, blocks + word boxes\nOne-call process + doctor")):
        b.text(x, 638, heading, 26, weight="bold")
        b.text(x, 688, body, 22, color=GRAY)
    b.text(65, 846, "02  Small core, explicit optional backends", 31, color=TEAL, weight="bold")
    b.box(65, 910, 1270, 165, fill=MINT)
    b.text(93, 935, "Text", 30, weight="bold")
    b.arrow(230, 987, 320, 987)
    b.text(345, 935, "Prepare / segment / tag / retrieve", 27, weight="bold")
    b.text(345, 992, "Offline, standard-library inference", 24, color=GRAY)
    b.arrow(1005, 987, 1085, 987)
    b.text(1110, 938, "Results", 28, weight="bold")
    b.text(1110, 994, "with spans", 23, color=GRAY)
    b.text(65, 1105, "Optional OCR: Pillow + PDFium + Tesseract with Khmer language data.", 23, color=GRAY)
    b.text(65, 1150, "Optional translation / generated answers: explicitly configure a service or local model.", 23, color=GRAY)
    b.text(65, 1238, "03  Evidence with visible limits", 31, color=TEAL, weight="bold")
    rows = [("Word segmentation", "{:.2f}% F1".format(metrics["segmentation"][1]),
             "khPOS OPEN; 1,000 sentences / 10,778 tokens"),
            ("Native POS, gold word boundaries", "{:.2f}%".format(metrics["native_pos"]),
             "Purged khPOS CLOSE; 1,000 sentences / 10,397 tokens"),
            ("OCR character error rate", "{:.2f}% CER".format(metrics["ocr_cer"][1]),
             "40 KHOB images = 10 documents x 4 variants; lower is better")]
    for y, (label, value, scope) in zip((1315, 1412, 1509), rows):
        b.line(65, y - 18, 1335, y - 18)
        b.text(65, y, label, 25, weight="bold")
        b.text(725, y - 3, value, 29, color=TEAL, weight="bold")
        b.text(65, y + 44, scope, 21, color=GRAY)
    b.box(65, 1625, 1270, 135, fill=BLUE)
    b.text(92, 1646, "Windows / macOS / Linux: fresh native installations passed.", 26, weight="bold")
    b.text(92, 1693, "Each OS: 203 core tests + 217 extras tests passed; 19 / 5 skipped.\nActual OCR + native POS executed; 2,000 compact-POS sentences replayed per OS.", 21, color=GRAY)
    b.text(65, 1792, "Native joint word/POS F1: {:.2f}%; mapped public POS: {:.2f}% at gold boundaries.".format(
        metrics["native_joint"], metrics["public_pos"]), 21, color=GRAY)
    b.text(65, 1833, "Role hints are heuristic. OCR is Tesseract-based; general sub-10% CER is not established.", 21, color=GRAY)
    b.line(65, 1882, 1335, 1882)
    b.text(65, 1904, "Nimol Thuon  |  github.com/back-kh/khmereasytools  |  " + date, 21, weight="bold")
    b.text(65, 1948, "MIT software; CC BY-NC-SA 4.0 trained POS weights. Source: TAGGER, IMPROVEMENTS and VALIDATION guides.", 18, color=GRAY)
    b.save(output / "poster", "KhmerEasyTools technical overview - A3 poster", date=date, pdf=True, svg=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--khmer-font", type=Path, required=True)
    parser.add_argument("--date", default="2026-10-20")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/assets")
    args = parser.parse_args()
    datetime.fromisoformat(args.date)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    metrics, sources = evidence()
    khmer = KhmerOutlines(args.khmer_font)
    hero(output, metrics, khmer, args.date)
    architecture(output, args.date)
    example = workflow(output, khmer, args.date)
    comparisons(output, metrics, args.date)
    poster(output, metrics, khmer, args.date)
    assets = {p.name: dict(bytes=p.stat().st_size, sha256=digest(p))
              for p in sorted(output.iterdir()) if p.suffix in (".svg", ".png", ".pdf")}
    manifest = dict(date=args.date, source_version=ket.__version__, sources_sha256=sources,
                    metrics=metrics, documented_example=example, assets=assets,
                    rendering=dict(matplotlib=matplotlib.__version__, fonttools=fontTools.__version__,
                                   uharfbuzz=hb.__version__, font_filename=args.khmer_font.name,
                                   font_sha256=digest(args.khmer_font)),
                    notes=["Existing results only; no new dataset, training or accuracy experiment.",
                           "Each comparison panel has its own metric, sample and limitations.",
                           "Khmer glyphs are shaped and outlined; the font file is not bundled."])
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(output=str(output), assets=len(assets), metrics=metrics), indent=2))


if __name__ == "__main__":
    main()
