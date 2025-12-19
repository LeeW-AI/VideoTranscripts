from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

app = Flask(__name__)

@app.route("/transcript")
def transcript():
    video_id = request.args.get("videoId")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(t["text"] for t in transcript)
        return jsonify({"transcript": text})

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts disabled"}), 404
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found"}), 404
    except VideoUnavailable:
        return jsonify({"error": "Video unavailable"}), 404

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
