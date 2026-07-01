# signals.py
import os
import json
from groq import Groq
from dotenv import load_dotenv
import re
import statistics

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def llm_signal(text: str) -> float:
    """
    Returns a float 0-1: probability the text is AI-generated.
    """
    prompt = f"""You are an AI text detector. Analyze the following text and estimate 
the probability that it was written by an AI rather than a human.

Respond with ONLY a JSON object in this exact format, nothing else:
{{"ai_probability": 0.0}}

Text to analyze:
\"\"\"{text}\"\"\"
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    raw = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(raw)
        score = float(parsed["ai_probability"])
        return max(0.0, min(1.0, score))  # clamp to [0,1]
    except (json.JSONDecodeError, KeyError, ValueError):
        # fallback if model doesn't return clean JSON
        print(f"Could not parse LLM response: {raw}")
        return 0.5
def stylometry_signal(text: str) -> float:
    """
    Returns a float 0-1: probability the text is AI-generated,
    based on average sentence length and structural uniformity.
    """
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) < 2:
        return 0.5  # not enough data to judge

    lengths = [len(s.split()) for s in sentences]
    avg_len = statistics.mean(lengths)
    variance = statistics.variance(lengths) if len(lengths) > 1 else 0

    # longer average sentence length -> more formal/AI-typical
    avg_len_score = min(avg_len / 25, 1.0)

    # lower variance -> more uniform -> more AI-typical
    variance_score = 1 - min(variance / 50, 1.0)

    combined = 0.6 * avg_len_score + 0.4 * variance_score
    return max(0.0, min(1.0, combined))