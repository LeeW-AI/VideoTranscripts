# new version 23:03 19th Dec

from flask import Flask, request, jsonify
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
import os
import requests
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

        # 1️⃣ Build raw text FIRST
        text = " ".join(item.text for item in data)

        # 2️⃣ Clean the text
        cleaned_text = re.sub(r"[♬♪]", "", text)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        return jsonify({
            "videoId": video_id,
            "transcript": cleaned_text
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


def get_channel_id(channel_name: str) -> str | None:
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        return None

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": channel_name,
        "type": "channel",
        "maxResults": 1,
        "key": api_key
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()

    items = r.json().get("items", [])
    if not items:
        return None

    return items[0]["snippet"]["channelId"]

def get_latest_videos(channel_id: str, limit: int):
    api_key = os.environ.get("YOUTUBE_API_KEY")

    url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "order": "date",
        "type": "video",
        "maxResults": limit,
        "key": api_key
    }

    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()

    videos = []
    for item in r.json().get("items", []):
        videos.append({
            "videoId": item["id"]["videoId"],
            "title": item["snippet"]["title"]
        })

    return videos

def fetch_clean_transcript(video_id: str) -> str | None:
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except:
            transcript = transcript_list.find_generated_transcript(['en'])

        data = transcript.fetch()
        text = " ".join(item.text for item in data)

        # clean text
        text = re.sub(r"[♬♪]", "", text)
        text = re.sub(r"\s+", " ", text).strip()

        return text

    except Exception:
        return None

@app.route("/youtube-query", methods=["POST"])
def youtube_query():
    payload = request.get_json(silent=True) or {}

    action = payload.get("action")
    channel_name = payload.get("channel_name")
    limit = int(payload.get("limit", 3))

    if not action or not channel_name:
        return jsonify({"error": "Missing action or channel_name"}), 400

    channel_id = get_channel_id(channel_name)
    if not channel_id:
        return jsonify({"error": "Channel not found"}), 404

    videos = get_latest_videos(channel_id, limit)

    # 1️⃣ LIST TITLES ONLY
    if action == "list_titles":
        titles = [v["title"] for v in videos]

        spoken = f"The latest {len(titles)} videos from {channel_name} are: "
        spoken += ". ".join(titles)

        return jsonify({
            "spoken_response": spoken,
            "videos": videos
        })

    # 2️⃣ SUMMARISE VIDEOS
    if action == "summarise":
        transcripts = []

        for v in videos:
            t = fetch_clean_transcript(v["videoId"])
            if t:
                transcripts.append(t)

        if not transcripts:
            return jsonify({
                "spoken_response": "I couldn’t retrieve transcripts for the latest videos."
            })

        combined_text = "\n\n".join(transcripts)

        # Ask OpenAI for a spoken summary
        headers = {
            "Authorization": f"Bearer {os.environ.get('OPENAI_API_KEY')}",
            "Content-Type": "application/json"
        }

        body = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "Summarise the following YouTube content into a concise, spoken-friendly overview."
                },
                {
                    "role": "user",
                    "content": combined_text[:12000]  # safety limit
                }
            ]
        }

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30
        )
        r.raise_for_status()

        summary = r.json()["choices"][0]["message"]["content"]

        return jsonify({
            "spoken_response": summary,
            "videos": videos
        })

    return jsonify({"error": "Unknown action"}), 400

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
