# New version 22:57

from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
import os
import re

app = Flask(__name__)

@app.route("/transcript")
def transcript():
    video_id = request.args.get("videoId")

    if not video_id:
        return jsonify({"error": "Missing videoId"}), 400

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Prefer manually created English transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(['en'])

        data = transcript.fetch()

        # IMPORTANT: v1.2.3 objects use .text (not dict access)
        # use cleaned text version for json
        cleaned_text = re.sub(r"[♬♪]", "", text)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
        cleaned_text = " ".join(item.text for item in data)

        return jsonify({
            "videoId": video_id,
            "transcript": text
        })

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts disabled"}), 404
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found"}), 404
    except VideoUnavailable:
        return jsonify({"error": "Video unavailable"}), 404
    except Exception as e:
        return jsonify({
            "error": "Transcript fetch failed",
            "details": str(e)
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
