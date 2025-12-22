# Latest stable version – summarise fixes applied

# Latest version 22nd Dec 01:29


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

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def clean_text(text: str) -> str:
    text = re.sub(r"[♬♪]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_video_id(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
    return match.group(1) if match else None


def extract_playlist_id(url: str) -> str | None:
    match = re.search(r"list=([\w-]+)", url)
    return match.group(1) if match else None


print("YT KEY PRESENT:", bool(os.environ.get("YOUTUBE_API_KEY")))
print("OPENAI KEY PRESENT:", bool(os.environ.get("OPENAI_API_KEY")))

# --------------------------------------------------
# Transcript Endpoint
# --------------------------------------------------

@app.route("/transcript")
def transcript():
    video_id = request.args.get("videoId")

    if not video_id:
        return jsonify({"error": "Missing videoId"}), 400

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        try:
            transcript = transcript_list.find_manually_created_transcript(['en'])
        except NoTranscriptFound:
            transcript = transcript_list.find_generated_transcript(['en'])

        data = transcript.fetch()
        text = " ".join(item.text for item in data)

        return jsonify({
            "videoId": video_id,
            "transcript": clean_text(text)
        })

    except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
        return jsonify({"error": "Transcript unavailable"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# --------------------------------------------------
# YouTube API Helpers
# --------------------------------------------------

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
        return clean_text(text)

    except Exception:
        return None


# --------------------------------------------------
# Unified YouTube Query Endpoint
# --------------------------------------------------

@app.route("/youtube-query", methods=["POST"])
def youtube_query():
    payload = request.get_json(silent=True) or {}

    action = (payload.get("action") or "").strip().lower()
    query = payload.get("query")
    video_url = payload.get("video_url")
    playlist_url = payload.get("playlist_url")
    limit = int(payload.get("limit", 3))

    # ----------------------------
    # Normalise action
    # ----------------------------
    if action in ["titles", "list", "list_titles"]:
        action = "list_titles"
    elif action in ["summary", "summarize", "summarise"]:
        action = "summarise"
    else:
        return jsonify({"error": f"Unknown action: {action}"}), 400

    # ----------------------------
    # Resolve target videos
    # ----------------------------
    videos = []

    if video_url:
        video_id = extract_video_id(video_url)
        if not video_id:
            return jsonify({"error": "Invalid video URL"}), 400
        videos = [{"videoId": video_id, "title": "Provided video"}]

    elif playlist_url:
        return jsonify({"error": "Playlist support not implemented"}), 400

    elif query:
        q = query.lower()

        limit_match = re.search(r"last\s+(\d+)", q)
        if limit_match:
            limit = int(limit_match.group(1))

        channel_name = None

        handle_match = re.search(r"@([\w\d_]+)", query)
        if handle_match:
            channel_name = handle_match.group(1)

        if not channel_name and "channel" in q:
            words = query.split()
            for i, w in enumerate(words):
                if w.lower() == "channel" and i > 0:
                    channel_name = words[i - 1]
                    break

        if not channel_name:
            channel_name = re.sub(
                r"\b(youtube|videos?|latest|summari[sz]e|from|the)\b",
                "",
                query,
                flags=re.IGNORECASE
            ).strip()

        channel_id = get_channel_id(channel_name)
        if not channel_id:
            return jsonify({"error": "Channel not found"}), 404

        videos = get_latest_videos(channel_id, limit)

    else:
        return jsonify({"error": "No target specified"}), 400

    if not videos:
        return jsonify({"error": "No videos found"}), 404

    # ----------------------------
    # LIST TITLES
    # ----------------------------
    if action == "list_titles":
        titles = [v["title"] for v in videos]
        spoken = f"The latest {len(titles)} videos are: " + ". ".join(titles)

        return jsonify({
            "spoken_response": spoken,
            "videos": videos
        })

    # ----------------------------
    # SUMMARISE
    # ----------------------------
    transcripts = []
    for v in videos:
        t = fetch_clean_transcript(v["videoId"])
        if t:
            transcripts.append(t)

    is_single_video = len(videos) == 1

    if is_single_video and transcripts:
        prompt = f"""
Summarise the following YouTube video transcript in a concise, spoken-friendly way.

Transcript:
{transcripts[0][:12000]}
""".strip()

    elif transcripts:
        prompt = f"""
Summarise the following YouTube videos into a concise spoken overview.
Highlight common themes and key points.

Content:
{chr(10).join(transcripts)[:12000]}
""".strip()

    else:
        titles = [v["title"] for v in videos]
        prompt = f"""
Based only on the following YouTube video titles, infer the main topics
and provide a concise spoken summary. Do not mention missing transcripts.

Titles:
{chr(10).join(titles)}
""".strip()

    openai_key = os.environ.get("OPENAI_API_KEY")
    if not openai_key:
        return jsonify({"error": "OPENAI_API_KEY not configured"}), 500

    #project_id = os.environ.get("OPENAI_PROJECT_ID")
    #if not project_id:
    #    return jsonify({"error": "OPENAI_PROJECT_ID not configured"}), 500

    # ----------------------------
    # OpenAI Responses API
    # ----------------------------
    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {openai_key}",  
                "Content-Type": "application/json",
                #"OpenAI-Project": os.environ.get("OPENAI_PROJECT_ID"),

            },
            json={
                "model": "gpt-4.1-mini",
                "input": prompt
            },
            timeout=30
        )
        r.raise_for_status()

        data = r.json()

        summary = None

        for item in data.get("output", []):
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    summary = block.get("text")
                    break
            if summary:
                break

        if not summary:
            raise ValueError("No output_text found in OpenAI response")
    
    except requests.exceptions.HTTPError as e:
        return jsonify({
            "error": "OpenAI HTTP error",
            "details": str(e),
            "status_code": e.response.status_code
        }), 502

    except requests.exceptions.RequestException as e:
        return jsonify({
            "error": "OpenAI network error",
            "details": str(e)
        }), 502

    except Exception as e:
        return jsonify({
            "error": "OpenAI response parsing error",
            "details": str(e)
        }), 500

    return jsonify({
        "spoken_response": summary,
        "videos": videos,
        "fallback": None if transcripts else "titles_only"
    })


# --------------------------------------------------
# Health Check
# --------------------------------------------------

@app.route("/youtube-test")
def youtube_test():
    return jsonify({"ok": True, "message": "YouTube backend is alive"})


# --------------------------------------------------
# App Entry
# --------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
