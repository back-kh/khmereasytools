"""Render the synthetic integration fixture with Pango and an installed font.

Requires pango-view, Pillow, ReportLab, and Khmer OS Content. Font binaries are not
redistributed. The supplied PNG is synthetic test data, not a real scan corpus.
"""
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops


def main():
    target = Path(__file__).resolve().parents[1] / "tests/fixtures/khmer_page.png"
    lines = ["ភាសាខ្មែរ", "ខ្ញុំស្រឡាញ់ភាសាខ្មែរ", "សាលារៀននៅប្រទេសកម្ពុជា", "សិស្សអានសៀវភៅ"]
    page = Image.new("RGB", (1400, 800), "white")
    regions = []
    with tempfile.TemporaryDirectory() as directory:
        for index, text in enumerate(lines):
            path = Path(directory) / "line.png"
            subprocess.run(["pango-view", "--no-display", "--font", "Khmer OS Content 30",
                            "--dpi", "150", "--text", text, "--margin", "0", "--output", str(path)], check=True)
            with Image.open(path) as rendered:
                rendered = rendered.convert("RGB")
                box = ImageChops.difference(rendered, Image.new("RGB", rendered.size, "white")).getbbox()
                x, y = 80, 60 + index * 170
                page.paste(rendered, (x, y))
                regions.append(dict(text=text, box=[x + box[0], y + box[1], box[2] - box[0], box[3] - box[1]]))
    page.save(target)
    from reportlab.pdfgen.canvas import Canvas
    canvas = Canvas(str(target.with_name("khmer_document.pdf")), pagesize=(700, 400), invariant=1)
    for _ in range(2):
        canvas.drawImage(str(target), 0, 0, width=700, height=400)
        canvas.showPage()
    canvas.save()
    target.with_suffix(".json").write_text(json.dumps(regions, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
