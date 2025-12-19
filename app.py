print("🚀 UPDATED APP.PY LOADED")

from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

@app.route("/transcript")
def transcript():
    video_id = request.args.get("videoId")

    if not video_id:
        return jsonify({"error": "Missing videoId"}), 400

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Prefer manually created English transcript, fallback to auto
        transcript = None
        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except:
            transcript = transcript_list.find_generated_transcript(['en'])

        entries = transcript.fetch()
        text = " ".join(item["text"] for item in entries)

        return jsonify({
            "videoId": video_id,
            "transcript": text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/")
def home():
    return {
        "status": "ok",
        "endpoint": "/transcript?videoId=VIDEO_ID"
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
