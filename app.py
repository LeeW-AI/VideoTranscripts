from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.exceptions import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
import os

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
        transcript = None
        for t in transcript_list:
            if t.language_code == "en" and not t.is_generated:
                transcript = t
                break

        # Fallback to first available transcript
        if transcript is None:
            transcript = next(iter(transcript_list))

        data = transcript.fetch()
        text = " ".join(item["text"] for item in data)

        return jsonify({
            "videoId": video_id,
            "language": transcript.language,
            "generated": transcript.is_generated,
            "transcript": text
        })

    except TranscriptsDisabled:
        return jsonify({"error": "Transcripts are disabled"}), 404
    except NoTranscriptFound:
        return jsonify({"error": "No transcript found"}), 404
    except VideoUnavailable:
        return jsonify({"error": "Video unavailable"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
