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
        text = " ".join([item["text"] for item in transcript])

        return jsonify({
            "videoId": video_id,
            "transcript": text
        })

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

@app.route("/")
def home():
    return {
        "status": "ok",
        "endpoints": {
            "/transcript": "GET ?videoId=VIDEO_ID"
        }
    }
