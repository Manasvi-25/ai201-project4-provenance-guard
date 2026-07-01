def combine_scores(llm_score: float, stylometry_score: float) -> float:
    """
    Combines both signals into a single confidence score using
    the weighted average defined in planning.md.
    """
    return round(0.7 * llm_score + 0.3 * stylometry_score, 3)


def get_attribution_and_label(confidence: float) -> tuple[str, str]:
    """
    Maps a confidence score to an attribution bucket and transparency label text.
    """
    if confidence >= 0.70:
        attribution = "likely_ai"
        label = ("This content is likely AI-generated. Our system found strong "
                  "signs of AI authorship, but no detector is 100% accurate.")
    elif confidence >= 0.35:
        attribution = "uncertain"
        label = ("We're not confident whether this content was written by a human "
                  "or AI. Read it with that uncertainty in mind.")
    else:
        attribution = "likely_human"
        label = "This content shows strong signs of human authorship."

    return attribution, label