"""Evaluation-only output normalization and paired document summaries."""
from collections import defaultdict
from html.parser import HTMLParser
import re
import statistics

from evaluation_metrics import aggregate_text, text_score


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"style", "script"}:
            self.hidden += 1
        if tag in {"p", "div", "br", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.hidden = max(0, self.hidden - 1)
        if tag in {"p", "div", "tr", "li", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def visible_text(output):
    """Strip serialization only; never repair or suppress recognized words."""
    output = re.sub(r"(?m)^\s*```[^\n]*$", "", output)
    output = re.sub(r"(?m)^\s*#{1,6}\s+", "", output)
    output = re.sub(r"(?m)^\s*[-*+]\s+", "", output)
    output = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", output)
    output = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", output)
    output = output.replace("**", "").replace("__", "")
    output = re.sub(r"(?m)^\s*\|[\s:|\-]+\|\s*$", "", output)
    output = "\n".join(line.replace("|", " ") if line.count("|") >= 2 else line
                       for line in output.splitlines())
    parser = VisibleText()
    parser.feed(output)
    return "\n".join(line.strip() for line in "".join(parser.parts).splitlines() if line.strip())


def summarize(records):
    groups = defaultdict(list)
    for record in records:
        groups[(record["collection"], record["system"])].append(record)
        if record["collection"] == "churro-sleuk":
            groups[("churro-sleuk-" + record["source_split"], record["system"])].append(record)
    result = {}
    for (collection, system), rows in sorted(groups.items()):
        item = aggregate_text([row["score"] for row in rows])
        item.update(failures=sum(bool(r["error"]) for r in rows),
                    empty=sum(not r["prediction"].strip() for r in rows),
                    capped=sum(bool(r.get("capped")) for r in rows),
                    capped_unknown=sum(r.get("capped") is None for r in rows),
                    groups=len({r["group"] for r in rows}),
                    median_seconds=statistics.median(r["seconds"] for r in rows),
                    total_seconds=sum(r["seconds"] for r in rows))
        result.setdefault(collection, {})[system] = item
    return result


def scored_record(page, system, prediction, seconds, error=None, **extra):
    # All failed pages retain their original full reference denominator.
    return dict(id=page["id"], collection=page["collection"], group=page["group"],
                source_split=page["source_split"], system=system, prediction=prediction,
                seconds=seconds, error=error,
                score=text_score(page["reference"], prediction), **extra)
