#!/usr/bin/env python3
"""Measure the writing features of local MCM/ICM award papers before turning any into a rule.

Why this exists: the CUMCM Kit learned that a rule tuned on synthetic fixtures proves only
that it is implemented as intended, not that it is right. O papers are correct by
definition, so any rule that fires on them is suspect. Several conventions also differ
between the two contests (MCM papers label every assumption with a "Justification", which
CUMCM award papers never do), so nothing is ported without being measured here first.

    python scripts/measure_award_corpus.py
    python scripts/measure_award_corpus.py --root "D:/documents/MCM&ICM/历年美赛优秀论文" --out reports/award_corpus_measurements.md

Only papers with a usable text layer are measured (>= 12 pages, >= 3000 words), from 2018
on. The report lists per-feature distributions; the Kit's thresholds cite it.
"""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
from pathlib import Path
import sys

DEFAULT_ROOT = Path("D:/documents/MCM&ICM/历年美赛优秀论文")
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "MCM_Workflow_Automation_Kit"))

# The rules are imported from the Kit, never copied: a copied rule drifts, and a calibration
# of a drifted copy is worse than none.
from mcm_workflow_kit.paper_hygiene_checker import (  # noqa: E402
    DASHES,
    HEDGES,
    MACHINE_PHRASES,
    TEAM_FACING as KIT_TEAM_FACING,
    title_of,
)

WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
ACRONYM_RE = re.compile(r"(?<![A-Za-z])[A-Z][A-Za-z0-9-]*[A-Z][A-Za-z0-9-]*(?![A-Za-z])")
NOT_METHOD_ACRONYMS = {
    "MCM", "ICM", "COMAP", "USA", "US", "UK", "UN", "EU", "GDP", "TEAM", "PAGE", "OF",
    "SUMMARY", "SHEET", "PROBLEM", "CHOSEN", "CONTROL", "NUMBER", "AI",
}
REPEAT = re.compile(r"\b([A-Za-z]{3,})\s+\1\b", re.I)
CAPTION = re.compile(r"^\s*(Figure|Fig\.|Table)\s*(\d+)\s*[:.]\s*(.*)$")
MS_RUNTIME, SOLVER, SCRIPT_NAME = (regex for _label, regex in MACHINE_PHRASES)
SNAKE = re.compile(r"(?<![A-Za-z0-9])[a-z][a-z0-9]*_[a-z0-9_]+(?![A-Za-z0-9])")


def run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True).stdout.decode("utf-8", "replace")


def classify(rel: str) -> tuple[int | None, str]:
    year = re.search(r"(20\d\d)", rel)
    letter = re.search(r"20\d\d([A-F])\b|/([A-F])/|/([A-F])\.pdf$|_([A-F])_O", rel)
    problem = next((g for g in (letter.groups() if letter else ()) if g), "?")
    return (int(year.group(1)) if year else None), problem


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def captions(pages: list[str]) -> list[str]:
    out = []
    for page in pages:
        lines = page.splitlines()
        for index, line in enumerate(lines):
            match = CAPTION.match(line)
            if not match or len(match.group(3)) < 3:
                continue
            text = match.group(3)
            for follow in lines[index + 1:index + 4]:
                if not follow.strip() or CAPTION.match(follow):
                    break
                if len(follow.strip()) < 40 or text.rstrip().endswith((".", ":")):
                    break
                text += " " + follow.strip()
            out.append(text.strip())
    return out


def section_between(text: str, start: str, stop: str) -> str:
    m = re.search(start, text, re.I)
    if not m:
        return ""
    rest = text[m.end():]
    n = re.search(stop, rest, re.I)
    return rest[: n.start()] if n else rest[:3000]


def bullets(block: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:•|◦|▪|●|-\s|\(\d+\)|\d+\.\s|\d+\))", block))


def measure(pdf: Path) -> dict | None:
    text = run(["pdftotext", "-enc", "UTF-8", str(pdf), "-"])
    words = WORD_RE.findall(text)
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    if len(pages) < 12 or len(words) < 3000:
        return None
    refs_at = next((i for i, p in enumerate(pages) if re.search(r"(?m)^\s*(?:\d+\s*)?References\s*$", p) and i > 3), len(pages))
    body = pages[1:refs_at]
    per_page = [len(WORD_RE.findall(p)) for p in body]
    flat = " ".join(pages[:refs_at])
    n_words = len(WORD_RE.findall(flat)) or 1
    first = pages[0]
    summary = first
    kw = re.search(r"Key\s*words?\s*[:：]", summary, re.I)
    summary_body = summary[: kw.start()] if kw else summary
    acronyms = {a for a in ACRONYM_RE.findall(summary_body) if a.upper() not in NOT_METHOD_ACRONYMS and not a.isdigit()}
    # The 2026 ProbA draft claimed an LHS-Monte Carlo sensitivity analysis in the summary that
    # the body never showed. Every method acronym the summary names should reappear in the body.
    body_text = " ".join(pages[1:refs_at])
    missing_in_body = sorted(a for a in acronyms if not re.search(rf"(?<![A-Za-z]){re.escape(a)}(?![A-Za-z])", body_text))
    control = re.findall(r"\b(\d{7})\b", first[:2000])
    control_no = control[0] if control else ""
    header_hits = sum(1 for p in pages[1:refs_at] if control_no and control_no in "\n".join(p.splitlines()[:4]))
    strengths = section_between(flat, r"Strengths?\b", r"Weakness|Limitation|Improvement|Future|Conclusion|References")
    weakness = section_between(flat, r"Weakness(?:es)?\b|Limitations?\b", r"Improvement|Extension|Future|Conclusion|Letter|Memo|References|Promotion")
    caps = captions(pages[:refs_at])
    fig_caps = [c for c in caps if c]
    rot = run(["pdfinfo", "-f", "1", "-l", str(len(pages)), str(pdf)])
    sizes = re.findall(r"Page\s+\d+\s+size:\s+([\d.]+)\s+x\s+([\d.]+)", rot)
    rots = re.findall(r"Page\s+\d+\s+rot:\s+(\d+)", rot)
    landscape = sum(1 for (w, h), r in zip(sizes, rots or ["0"] * len(sizes))
                    if (float(w) > float(h)) != (int(r) in (90, 270)))
    title = title_of(first)
    return {
        "pages": len(pages),
        "counted": refs_at,
        "words": n_words,
        "median_words_page": statistics.median(per_page) if per_page else 0,
        "p75_words_page": percentile(per_page, 0.75),
        "summary_words": len(WORD_RE.findall(summary_body)),
        "summary_acronyms": len(acronyms),
        "summary_acronyms_missing": missing_in_body,
        "summary_numbers": len(re.findall(r"\d+(?:\.\d+)?%?", summary_body)),
        "keywords": bool(kw),
        "title": title,
        "title_words": len(WORD_RE.findall(title)),
        "title_colon": ":" in title,
        "title_dash": bool(DASHES.search(title)),
        "hedges": len(HEDGES.findall(flat)),
        "hedge_rate": 1e4 * len(HEDGES.findall(flat)) / n_words,
        "team_facing": [m.group(0) for _label, regex in KIT_TEAM_FACING for m in regex.finditer(flat)],
        "ms": len(MS_RUNTIME.findall(flat)),
        "scripts": SCRIPT_NAME.findall(flat)[:5],
        "snake": len(SNAKE.findall(flat)),
        "solver": len(SOLVER.findall(flat)),
        "repeats": len(REPEAT.findall(flat)),
        "captions": [len(WORD_RE.findall(c)) for c in fig_caps],
        "caption_multi": sum(1 for c in fig_caps if len(re.findall(r"[a-z)]\.\s+[A-Z]", c)) >= 1),
        "strength_items": bullets(strengths),
        "weakness_items": bullets(weakness),
        "control_header_share": header_hits / max(1, len(pages[1:refs_at])),
        "landscape_pages": landscape,
        "ai_report": bool(re.search(r"Report on (?:the )?Use of AI", text, re.I)),
        "justification": len(re.findall(r"\bJustification\b", flat)),
    }


def dist(values: list[float]) -> str:
    if not values:
        return "n/a"
    return (f"min {min(values):.2f} · P25 {percentile(values, .25):.2f} · median {statistics.median(values):.2f}"
            f" · P75 {percentile(values, .75):.2f} · P90 {percentile(values, .9):.2f} · max {max(values):.2f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    parser.add_argument("--out", default=str(REPO / "reports" / "award_corpus_measurements.md"))
    parser.add_argument("--min-year", type=int, default=2018)
    parser.add_argument("--compare", nargs="*", default=[], help="Extra PDFs (our own papers) measured the same way")
    args = parser.parse_args()
    root = Path(args.root)
    rows = []
    for pdf in sorted(root.rglob("*.pdf")):
        rel = pdf.relative_to(root).as_posix()
        if re.search(r"UMAP|翻译|解析|Problem_C|solutions|/(?:19|20)\d\d(?:MCM|ICM|mcm)", rel):
            continue
        year, problem = classify(rel)
        if year is None or year < args.min_year:
            continue
        rec = measure(pdf)
        if rec is None:
            continue
        rec.update(rel=rel, year=year, problem=problem)
        rows.append(rec)

    def col(key):
        return [float(r[key]) for r in rows]

    all_caps = [c for r in rows for c in r["captions"]]
    ratio = [r["strength_items"] / r["weakness_items"] for r in rows if r["strength_items"] and r["weakness_items"]]
    lines = [
        "# MCM/ICM award corpus measurements",
        "",
        f"- Papers measured: **{len(rows)}** (text layer usable, {args.min_year}+), "
        f"years {sorted({r['year'] for r in rows})}",
        f"- Generated by `scripts/measure_award_corpus.py`; rules in the Kit cite these numbers.",
        "",
        "| Feature | Distribution across papers |",
        "| --- | --- |",
        f"| Counted pages (to References) | {dist(col('counted'))} |",
        f"| Words per body page, median | {dist(col('median_words_page'))} |",
        f"| Words per body page, P75 | {dist(col('p75_words_page'))} |",
        f"| Summary words (before Keywords) | {dist(col('summary_words'))} |",
        f"| Distinct acronyms in summary | {dist(col('summary_acronyms'))} |",
        f"| Numbers in summary | {dist(col('summary_numbers'))} |",
        f"| Keywords line on page 1 | {sum(r['keywords'] for r in rows)}/{len(rows)} |",
        f"| Title words (title found in {sum(1 for r in rows if r['title'])}) | {dist([float(r['title_words']) for r in rows if r['title']])} |",
        f"| Title with colon / with dash | {sum(r['title_colon'] for r in rows if r['title'])} / {sum(r['title_dash'] for r in rows if r['title'])} |",
        f"| Hedges per 10k words | {dist(col('hedge_rate'))} |",
        f"| Papers with 0 hedges | {sum(1 for r in rows if r['hedges'] == 0)}/{len(rows)} |",
        f"| Caption words (all captions, n={len(all_caps)}) | {dist([float(c) for c in all_caps])} |",
        f"| Captions with 2+ sentences | {sum(r['caption_multi'] for r in rows)} of {len(all_caps)} |",
        f"| Captions over 40 / 60 words | {sum(1 for c in all_caps if c > 40)} / {sum(1 for c in all_caps if c > 60)} of {len(all_caps)}; P95 {percentile([float(c) for c in all_caps], .95):.0f} |",
        f"| Summaries with fewer than 3 numbers | {sum(1 for r in rows if r['summary_numbers'] < 3)}/{len(rows)} |",
        f"| Summary acronyms never used in the body | {sum(1 for r in rows if r['summary_acronyms_missing'])}/{len(rows)} papers: {[(r['rel'], r['summary_acronyms_missing']) for r in rows if r['summary_acronyms_missing']][:8]} |",
        f"| Papers with 5+ hedges and > 3 per 10k words | {sum(1 for r in rows if r['hedges'] >= 5 and r['hedge_rate'] > 3)}/{len(rows)} |",
        f"| Titles over 16 words (extraction-checked below) | {[r['title'] for r in rows if r['title_words'] > 16][:5]} |",
        f"| Title with a dash | {[r['title'] for r in rows if r['title_dash']]} |",
        f"| Strengths/weaknesses item ratio (n={len(ratio)}) | {dist(ratio)} |",
        f"| Papers with strength list >= 2x weakness list | {sum(1 for x in ratio if x >= 2)}/{len(ratio)} |",
        f"| Team-facing / tool traces | {sum(1 for r in rows if r['team_facing'])} papers: {[ (r['rel'], r['team_facing'][:3]) for r in rows if r['team_facing']][:5]} |",
        f"| Millisecond runtimes | {sum(1 for r in rows if r['ms'])} papers |",
        f"| Script file names (.py/.m/.R) | {sum(1 for r in rows if r['scripts'])} papers: {[r['scripts'] for r in rows if r['scripts']][:4]} |",
        f"| snake_case tokens per paper | {dist(col('snake'))} |",
        f"| Solver-parameter strings | {sum(1 for r in rows if r['solver'])} papers |",
        f"| Repeated words ('the the') per paper | {dist(col('repeats'))} |",
        f"| Landscape pages | {sum(1 for r in rows if r['landscape_pages'])} papers |",
        f"| Control number in page header (share of body pages) | {dist(col('control_header_share'))} |",
        f"| 'Justification' mentions per paper | {dist(col('justification'))} |",
        f"| AI report section | {sum(r['ai_report'] for r in rows)}/{len(rows)} |",
        "",
        "## Per paper",
        "",
        "| Paper | Year | Prob | Counted pp | Words/pp (med) | Summary words | Acronyms | Hedges/10k | Title |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for r in sorted(rows, key=lambda x: (x["year"], x["problem"], x["rel"])):
        lines.append(
            f"| {r['rel']} | {r['year']} | {r['problem']} | {r['counted']} | {r['median_words_page']:.0f} | "
            f"{r['summary_words']} | {r['summary_acronyms']} | {r['hedge_rate']:.2f} | {r['title'][:60]} |"
        )
    if args.compare:
        lines.extend(["", "## Our papers, measured the same way", "",
                      "| Paper | Counted pp | Words/pp (med) | Words/pp (P75) | Summary words | Numbers | Hedges/10k | Title |",
                      "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"])
        for extra in args.compare:
            rec = measure(Path(extra))
            if rec is None:
                lines.append(f"| {extra} | (no usable text layer) |")
                continue
            lines.append(
                f"| {Path(extra).parent.parent.name} | {rec['counted']} | {rec['median_words_page']:.0f} | "
                f"{rec['p75_words_page']:.0f} | {rec['summary_words']} | {rec['summary_numbers']} | "
                f"{rec['hedge_rate']:.2f} | {rec['title'][:60]} |")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:40]))
    if args.compare:
        print("\n".join(lines[-(len(args.compare) + 4):]))
    print(f"\nwritten {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
