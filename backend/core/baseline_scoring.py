from typing import List, Any, Dict
from statistics import mean

def score_baseline(answers: List[dict], qmap: dict) -> tuple[Dict[str, float], List[str], List[str]]:
    # init container
    agg: Dict[str, list] = {}
    for facet in set(qmap.values()):
        agg[facet] = []

    # bucket answers by facet
    for ans in answers:
        qid = ans.get("qid")
        value = ans.get("value")
        facet = qmap.get(qid)
        if facet and value is not None:
            normalized = value / 5   # convert 1–5 → 0–1
            agg[facet].append(normalized)

    # compute mean per facet
    scores: Dict[str, float] = {}
    for facet, vals in agg.items():
        scores[facet] = round(mean(vals), 3) if vals else 0.0

    # strengths (top 1) and focus (bottom 2)
    sorted_facets = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    strengths = [sorted_facets[0][0]] if sorted_facets else []
    focus = [f for f, _ in sorted_facets[-2:]] if len(sorted_facets) >= 2 else []

    return scores, strengths, focus


def summarize_baseline(scores: dict) -> str:
    """
    Generate a human-readable summary of EQ facet scores.
    """
    if not scores:
        return "No scores available."

    sorted_facets = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top = sorted_facets[0][0]
    bottom_two = [f for f, _ in sorted_facets[-2:]] if len(sorted_facets) >= 2 else []

    summary = f"Your strongest area is {top.replace('_',' ').title()}."
    if bottom_two:
        summary += f" Focus on improving {', '.join(b.replace('_',' ').title() for b in bottom_two)}."
    return summary
