"""Flask endpoints exposing the resume–JD matching service."""

from __future__ import annotations

from flask import Flask, jsonify, request

from src.container import get_resume_matching_service


def create_app() -> Flask:
    """Create and configure the Flask application instance."""
    app = Flask(__name__)

    @app.get("/health")
    def health():
        """Return a simple JSON payload indicating the service is alive."""
        return jsonify({"status": "ok"})

    @app.post("/match")
    def match():
        """Evaluate a single resume provided as form text against a job description."""
        jd_text = request.form.get("jd_text", "")
        resume_text = request.form.get("resume_text", "")
        if not jd_text or not resume_text:
            return jsonify({"error": "jd_text and resume_text are required"}), 400

        svc = get_resume_matching_service()
        return jsonify(svc.match_text(jd_text=jd_text, resume_text=resume_text))

    @app.post("/match-files")
    def match_files():
        """Evaluate one or more uploaded resume files against a job description."""
        jd_text = request.form.get("jd_text", "")
        uploads = request.files.getlist("files")
        if not jd_text or not uploads:
            return jsonify({"error": "jd_text and files are required"}), 400

        pairs: list[tuple[str, bytes]] = []
        for f in uploads:
            pairs.append((f.filename, f.read()))

        svc = get_resume_matching_service()
        return jsonify(svc.match_files(jd_text=jd_text, files=pairs))

    return app


app = create_app()
