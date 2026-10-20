"""Pure evaluation helpers; never imported by the distributed toolkit."""
from collections import defaultdict
import hashlib
import math
import random
import statistics

from evaluation_metrics import aggregate_text


def stable_subset(names, count):
    names = sorted(set(names))
    return set(sorted(names, key=lambda name: hashlib.sha256(
        ("expanded-ocr-20261018/" + name).encode("utf-8")).digest())[:count])


def upright_dimensions(width, height, orientation):
    if orientation not in range(1, 9):
        raise ValueError("unknown_image_orientation")
    return (height, width) if orientation in {5, 6, 7, 8} else (width, height)


def polygon_bounds(xs, ys, width, height):
    if not isinstance(xs, list) or not isinstance(ys, list) or len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("malformed_polygon")
    points = []
    for x, y in zip(xs, ys):
        if isinstance(x, bool) or isinstance(y, bool):
            raise ValueError("malformed_polygon")
        try:
            x, y = float(x), float(y)
        except (ValueError, TypeError):
            raise ValueError("malformed_polygon")
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("nonfinite_polygon")
        if x < -1 or y < -1 or x > width or y > height:
            raise ValueError("polygon_outside_image")
        points.append((max(0, min(width - 1, x)), max(0, min(height - 1, y))))
    x0, y0 = math.floor(min(x for x, _ in points)), math.floor(min(y for _, y in points))
    x1 = min(width, math.ceil(max(x for x, _ in points)) + 1)
    y1 = min(height, math.ceil(max(y for _, y in points)) + 1)
    # Shoelace area rejects collinear/empty polygons, not merely empty bboxes.
    area = abs(sum(points[i][0] * points[(i + 1) % len(points)][1] -
                   points[(i + 1) % len(points)][0] * points[i][1]
                   for i in range(len(points)))) / 2
    if x1 - x0 < 2 or y1 - y0 < 2 or area < 1:
        raise ValueError("empty_polygon")
    return points, (x0, y0, x1, y1)


def aggregate_system(rows, system):
    scored = [row[system] for row in rows]
    value = aggregate_text(scored)
    rates = [row["codepoint_edits"] / row["reference_codepoints"]
             for row in scored if row["reference_codepoints"]]
    value.update(median_unit_cer=statistics.median(rates) if rates else None,
                 failures=sum(row.get("failed", False) for row in scored),
                 ocr_seconds=sum(row["seconds"] for row in scored))
    return value


def percentile(values, fraction):
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low, high = math.floor(position), math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def paired_interval(rows, replicates=5000, seed=20261018):
    clusters = defaultdict(lambda: [0, 0, 0])
    for row in rows:
        a, b = row["baseline"], row["toolkit"]
        if a["reference_codepoints"] != b["reference_codepoints"]:
            raise ValueError("Paired reference denominators differ")
        value = clusters[row["group"]]
        value[0] += a["reference_codepoints"]
        value[1] += a["codepoint_edits"]
        value[2] += b["codepoint_edits"]
    groups = [clusters[key] for key in sorted(clusters)]
    denominator = sum(g[0] for g in groups)
    if not groups or not denominator:
        raise ValueError("No reference characters for paired analysis")
    observed = 100 * sum(g[2] - g[1] for g in groups) / denominator
    rng, draws = random.Random(seed), []
    for _ in range(replicates):
        selected = [groups[rng.randrange(len(groups))] for _ in groups]
        size = sum(g[0] for g in selected)
        draws.append(100 * sum(g[2] - g[1] for g in selected) / size)
    return dict(source_groups=len(groups), toolkit_minus_baseline_cer_points=observed,
                percentile_95_interval=[percentile(draws, .025), percentile(draws, .975)],
                bootstrap_replicates=replicates, bootstrap_seed=seed,
                interpretation="Descriptive paired cluster interval; negative favors toolkit")


def summarize(rows):
    if not rows:
        raise ValueError("Cannot summarize an empty track")
    return dict(units=len(rows), source_images=len({r["source_id"] for r in rows}),
                baseline=aggregate_system(rows, "baseline"),
                toolkit=aggregate_system(rows, "toolkit"), paired=paired_interval(rows))
