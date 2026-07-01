# Provenance Guard — Planning

---
## Project Description

AI Content Provenance Detector is a backend system that classifies submitted creative text as likely AI-generated, likely human-written, or uncertain, and gives creators a way to appeal a classification they believe is wrong. It takes a piece of text, analyzes it using two independent detection signals, produces a confidence score instead of a binary verdict, generates a simple transparency label for readers, and logs both decisions and appeals for accountability.

---
## Detection Signals

I'm using two signals: an LLM-based judgment (Groq, llama-3.3-70b-versatile) and 
stylometric heuristics (pure Python).

**Signal 1 — LLM judgment.** I send the submitted text to Groq with a prompt asking it to estimate how likely the writing is to be AI-generated and return a score between 0 and 1. This captures things like writing style, flow, and overall coherence. The downside is that it's mostly judging based on how the text feels. An emotional AI-written piece might seem human, while a very formal or flat human-written piece could get flagged as AI. It can't actually verify who wrote the text, only make a prediction from the writing itself.

**Signal 2 — Stylometric heuristics.** The second signal is computed in pure Python and looks at the structure of the writing. It measures average sentence length 
and sentence-length variance, then combines them into a score from 0 to 1. AI-generated text tends to use longer, more uniform sentences, while human writing is usually shorter and more irregular. The downside is that it only looks at structure, not meaning, so naturally consistent writers, like ESL speakers or people with very formal writing styles, could be incorrectly flagged as AI.

**Combining them.** Both signals output a 0–1 score. I combine them with a weighted 
average: confidence = 0.7 * llm_score + 0.3 * stylometry_score. I weight the LLM 
signal higher because it captures semantic context that stylometry can't, but I 
keep stylometry in the mix specifically because it can catch cases where the LLM 
signal is fooled by tone.

---
## Uncertainty Representation

A confidence score represents the probability, on a 0–1 scale, that the submitted 
text is AI-generated, produced by the weighted combination of both signals described 
above.

Because a false positive (labeling a human's work as AI) is more damaging to a 
creator than a false negative, my thresholds are deliberately skewed to require more 
evidence before calling something "likely AI":

| Score range | Bucket        |
|--------------|---------------|
| 0.00 – 0.35  | Likely human  |
| 0.35 – 0.70  | Uncertain     |
| 0.70 – 1.00  | Likely AI     |

A score of 0.6, for example, means the signals lean toward AI but not strongly enough 
to state it definitively — it falls in the "Uncertain" bucket rather than being 
rounded up to "likely AI." This wide uncertain band is intentional: it protects 
human creators from being confidently mislabeled on borderline cases.

---
## Transparency Label Design

**Likely AI (score 0.70–1.00):**
> This content is likely AI-generated. Our system found strong signs of AI authorship, but no detector is 100% accurate.

**Uncertain (score 0.35–0.70):**
> We're not confident whether this content was written by a human or AI. Read it with that uncertainty in mind.

**Likely Human (score 0.00–0.35):**
> This content shows strong signs of human authorship.

The labels are meant to give readers more context, not act as a final verdict. Even the **Likely AI** label makes it clear that the result is only a prediction, since AI detection isn't perfect.

---
## Appeals Workflow
Any creator can appeal a classification through `POST /appeal` by providing:

- `content_id` for the submission
- `creator_reasoning`, explaining why they think the result is wrong

When an appeal is submitted, the system:

1. Marks the submission as **`under_review`**
2. Logs the appeal along with the original classification, confidence score, signal scores, and the creator's reasoning
3. Returns a confirmation that the appeal was received

A human reviewer can then use `GET /log` to view submissions with `status: "under_review"`, along with the original results, the creator's explanation, and a timestamp. This provides enough context to manually review the case without re-running the detector.

---
## Anticipated Edge Cases

1. **A highly polished human writer.** Someone like an academic or a writer who naturally writes in a very formal, structured style could be flagged as AI. Their writing might have consistent grammar, similar sentence lengths, and very little variation, which the stylometry signal interprets as an AI pattern even though it's completely human.

2. **Very simple writing.** A children's story, diary entry, or writing with short, repetitive sentences and basic vocabulary could also be misclassified as AI. Even though the simplicity comes from the writer's age or style, the system only sees the low structural variation and may incorrectly treat it as an AI signal.

---
## Architecture

**Submission flow:**
```
POST /submit {text, creator_id}
        ↓
   Signal 1: Groq LLM judgment
   (semantic/stylistic score, 0-1)
        ↓
   Signal 2: Stylometric heuristics
   (structural uniformity score, 0-1)
        ↓
   Confidence Scoring
   (weighted average: 0.7*llm + 0.3*stylometry)
        ↓
   Label Generation
   (maps score → Likely AI / Uncertain / Likely Human text)
        ↓
   Audit Log
   (writes: content_id, timestamp, attribution, confidence,
    individual signal scores, status)
        ↓
   Response {content_id, attribution, confidence, label}
```
**Appeal flow:**

```
POST /appeal {content_id, creator_reasoning}
↓
Look up original entry by content_id
↓
Update status → "under_review"
↓
Audit Log
(appends appeal_reasoning + status change to existing entry)
↓
Response {status: "under_review", confirmation}
```
A submission runs through both detection signals independently, gets combined into a 
single confidence score, and that score deterministically maps to one of three label 
texts before the whole decision is written to the audit log. An appeal doesn't 
re-run detection — it just attaches the creator's reasoning to the existing decision 
and flips its status, so a human reviewer can evaluate it manually later.

## AI Tool Plan

**M3 — Submission endpoint + first signal:**
- Give AI tool: Detection Signals section (Signal 1 description) + Architecture diagram
- Ask for: Flask app skeleton with `POST /submit` route stub, plus the Groq-based 
  signal 1 function (takes text, returns a 0-1 AI-probability score)
- Verify: call the signal 1 function directly with a few known human/AI test inputs 
  before wiring it into the endpoint; confirm output is a float in [0,1]

**M4 — Second signal + confidence scoring:**
- Give AI tool: Detection Signals section + Uncertainty Representation section + 
  Architecture diagram
- Ask for: stylometric signal function (sentence length variance, type-token ratio, 
  punctuation density → normalized 0-1 score) + the weighted-average scoring function
- Verify: run both signals against the 4 test inputs from the doc (clearly AI, 
  clearly human, 2 borderline) and confirm scores diverge meaningfully and match the 
  0.35/0.70 thresholds as intended

**M5 — Production layer:**
- Give AI tool: Transparency Label Design section + Appeals Workflow section + 
  Architecture diagram
- Ask for: label-generation function mapping confidence score → exact label text, 
  plus the `POST /appeal` endpoint (updates status, logs reasoning, returns 
  confirmation)
- Verify: submit test inputs spanning all 3 score ranges and confirm all 3 label 
  variants are reachable; submit a test appeal and confirm `GET /log` shows 
  `status: "under_review"` with `appeal_reasoning` populated
