"""Absolute-score prevalence among eligible scanned Earth grid cells."""
from __future__ import annotations


def terrain_commonality(rows, grid_ids):
    scores=[float(row['score_geo']) for row in rows if row['id'] in grid_ids]
    count=len(scores)
    n90=sum(score >= 90 for score in scores)
    n80=sum(score >= 80 for score in scores)
    share90=n90/count if count else None
    share80=n80/count if count else None
    explanation=None
    if share90 is not None and share90 >= .10:
        percent=f'{share90*100:.1f}'.rstrip('0').rstrip('.')
        explanation=(f'This terrain type is common in the scanned area ({percent}% of cells ≥ 90); '
                     'topography alone does not single out an analog — non-topographic properties '
                     '(e.g. ground ice, temperature) would be needed.')
    return {'eligible_cells':count,'count_ge_90':n90,'share_ge_90':share90,
            'count_ge_80':n80,'share_ge_80':share80,'explanation':explanation}
