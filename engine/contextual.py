"""Discount terrain similarity when high scores are common in the scanned grid."""


def commonality_factor(commonality: dict) -> float:
    share80 = commonality.get('share_ge_80')
    share90 = commonality.get('share_ge_90')
    if share80 is None or share90 is None:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (float(share80) + float(share90)) / 2.0))


def contextual_score(score_geo: float, commonality: dict) -> float:
    return float(score_geo) * commonality_factor(commonality)
