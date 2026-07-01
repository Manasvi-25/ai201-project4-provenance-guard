from flask import Flask, request, jsonify
import uuid
from datetime import datetime, timezone
from signals import llm_signal, stylometry_signal
from scoring import combine_scores, get_attribution_and_label
from audit_log import write_log_entry, get_log, update_log_entry
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

@app.route("/submit", methods=["POST"])
@limiter.limit("10 per minute;100 per day")
def submit():
    data = request.get_json()
    text = data.get("text")
    creator_id = data.get("creator_id")

    content_id = str(uuid.uuid4())

    llm_score = llm_signal(text)
    stylometry_score = stylometry_signal(text)
    confidence = combine_scores(llm_score, stylometry_score)
    attribution, label = get_attribution_and_label(confidence)

    log_entry = {
        "content_id": content_id,
        "creator_id": creator_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "attribution": attribution,
        "confidence": confidence,
        "llm_score": llm_score,
        "stylometry_score": stylometry_score,
        "status": "classified"
    }
    write_log_entry(log_entry)

    return jsonify({
        "content_id": content_id,
        "attribution": attribution,
        "confidence": confidence,
        "label": label
    })

@app.route("/log", methods=["GET"])
def log():
    return jsonify({"entries": get_log()})

@app.route("/appeal", methods=["POST"])
def appeal():
    data = request.get_json()
    content_id = data.get("content_id")
    creator_reasoning = data.get("creator_reasoning")

    if not content_id or not creator_reasoning:
        return jsonify({"error": "content_id and creator_reasoning are required"}), 400

    updated = update_log_entry(content_id, {
        "status": "under_review",
        "appeal_reasoning": creator_reasoning,
        "appeal_timestamp": datetime.now(timezone.utc).isoformat()
    })

    if not updated:
        return jsonify({"error": "content_id not found"}), 404

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "message": "Appeal received and logged for review."
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)