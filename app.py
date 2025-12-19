from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

@app.route("/transcript")
def transcript():
    video_id = request.args.get("videoId")
    if not video_id:
        return jsonify({"error": "Missing videoId"}), 400

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join([t["text"] for t in transcript])
        return jsonify({
            "videoId": video_id,
            "transcript": text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
