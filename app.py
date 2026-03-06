# app.py
from flask import Flask, render_template, request, jsonify, Response
import json
import os
from datetime import datetime
import threading
from queue import Queue

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# File path
LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), 'leaderboard.json')

# Thread-safe lock for file operations
leaderboard_lock = threading.Lock()

# In-memory leaderboard (loaded from JSON)
leaderboard = []

# SSE clients queue (for realtime updates)
clients = set()

def load_leaderboard():
    global leaderboard
    if not os.path.exists(LEADERBOARD_FILE):
        # Auto-create empty leaderboard file
        with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        leaderboard = []
        return

    try:
        with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Sort: highest score first, then lowest time
            data.sort(key=lambda x: (-x['score'], x['time_sec']))
            leaderboard = data
    except Exception as e:
        print(f"Leaderboard load error: {e}")
        leaderboard = []

def save_leaderboard():
    with leaderboard_lock:
        try:
            with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
                json.dump(leaderboard, f, ensure_ascii=False, indent=2)
            # Notify all connected clients
            broadcast_leaderboard()
        except Exception as e:
            print(f"Save error: {e}")

def broadcast_leaderboard():
    """Send updated leaderboard to all SSE clients"""
    for client in list(clients):
        try:
            client.put(json.dumps({"leaderboard": leaderboard}))
        except:
            clients.discard(client)

# Load leaderboard at startup
load_leaderboard()

# All 21 questions
QUESTIONS = [
    {"q": "রাসূল ﷺ এর পুরো নাম কী?", "options": ["আহমদ ইবনে আব্দুল্লাহ", "মুহাম্মদ ইবনে আব্দুল্লাহ", "মুহাম্মদ ইবনে উমর", "আব্দুল্লাহ ইবনে মুহাম্মদ"], "ans": 1},
    {"q": "রাসূল ﷺ কোথায় জন্মগ্রহণ করেন?", "options": ["মদিনা", "তাইফ", "মক্কা", "জেরুজালেম"], "ans": 2},
    {"q": "রাসূল ﷺ কত সালে জন্মগ্রহণ করেন?", "options": ["৫৬৫ খ্রি.", "৫৭০ খ্রি.", "৫৮০ খ্রি.", "৫৯০ খ্রি."], "ans": 1},
    {"q": "রাসূল ﷺ কোন মাসে জন্মগ্রহণ করেন?", "options": ["রজব", "রবিউল আউয়াল", "শাওয়াল", "রমাদান"], "ans": 1},
    {"q": "রাসূল ﷺ এর মাতার নাম কী?", "options": ["আমিনা বিনতে ওয়াহব", "হালিমা সাদিয়া", "খাদিজা বিনতে খুয়াইলিদ", "ফাতিমা বিনতে আসাদ"], "ans": 0},
    {"q": "রাসূল ﷺ কত বছর বয়সে নবুয়ত লাভ করেন?", "options": ["৩০ বছর", "৩৫ বছর", "৪০ বছর", "৪৫ বছর"], "ans": 2},
    {"q": "প্রথম ওহী কোথায় নাজিল হয়েছিল?", "options": ["উহুদ পাহাড়", "হেরা গুহা", "সাফা পাহাড়", "আরাফাত ময়দান"], "ans": 1},
    {"q": "প্রথম ওহী কে নিয়ে এসেছিলেন?", "options": ["জিবরাইল (আ.)", "মিকাইল (আ.)", "ইসরাফিল (আ.)", "আজরাইল (আ.)"], "ans": 0},
    {"q": "রাসূল ﷺ এর প্রথম স্ত্রী কে ছিলেন?", "options": ["আয়েশা বিনতে আবু বকর", "খাদিজা বিনতে খুয়াইলিদ", "হাফসা বিনতে উমর", "জয়নব বিনতে জাহশ"], "ans": 1},
    {"q": "রাসূল ﷺ মদিনায় হিজরত করেন কত সালে?", "options": ["৬১০ খ্রি.", "৬১৫ খ্রি.", "৬২২ খ্রি.", "৬৩০ খ্রি."], "ans": 2},
    {"q": "মদিনার আগের নাম কী ছিল?", "options": ["তাবুক", "ইয়াসরিব", "খায়বার", "বদর"], "ans": 1},
    {"q": "রাসূল ﷺ কত বছর নবুয়তের দায়িত্ব পালন করেন?", "options": ["২০ বছর", "২৩ বছর", "২৫ বছর", "৩০ বছর"], "ans": 1},
    {"q": "হযরত ফাতিমা (রা.) কার স্ত্রী ছিলেন?", "options": ["উসমান ইবনে আফফান", "আলী ইবনে আবি তালিব", "উমর ইবনে খাত্তাব", "তালহা ইবনে উবায়দুল্লাহ"], "ans": 1},
    {"q": "রাসূল ﷺ এর সবচেয়ে ছোট ছেলে কে ছিলেন?", "options": ["কাসিম", "আবদুল্লাহ", "ইবরাহিম", "হামজা"], "ans": 2},
    {"q": "রাসূল ﷺ এর দাদার নাম কী?", "options": ["আব্দুল মুত্তালিব", "হাশিম ইবনে আব্দে মানাফ", "আবু তালিব", "আব্বাস ইবনে আব্দুল মুত্তালিব"], "ans": 0},
    {"q": "রাসূল ﷺ কোথায় ইন্তেকাল করেন?", "options": ["মক্কা", "মদিনা", "তাইফ", "দামেস্ক"], "ans": 1},
    {"q": "রাসূল ﷺ কত বছর বয়সে ইন্তেকাল করেন?", "options": ["৬০ বছর", "৬২ বছর", "৬৩ বছর", "৬৫ বছর"], "ans": 2},
    {"q": "রাসূল ﷺ এর উপাধি কী ছিল?", "options": ["আল-আমিন", "আল-ফারুক", "আস-সিদ্দিক", "যুন-নুরাইন"], "ans": 0},
    {"q": "ইসলামের প্রথম খলিফা কে ছিলেন?", "options": ["উমর ইবনে খাত্তাব", "আলী ইবনে আবি তালিব", "আবু বকর", "উসমান ইবনে আফফান"], "ans": 2},
    {"q": "বদর যুদ্ধ কত হিজরিতে হয়েছিল?", "options": ["১ হিজরি", "২ হিজরি", "৩ হিজরি", "৫ হিজরি"], "ans": 1},
    {"q": "মক্কা বিজয় (ফতহ মক্কা) কত হিজরিতে হয়েছিল?", "options": ["৬ হিজরি", "৭ হিজরি", "৮ হিজরি", "৯ হিজরি"], "ans": 2}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/questions')
def get_questions():
    return jsonify(QUESTIONS)

@app.route('/api/submit', methods=['POST'])
def submit_score():
    try:
        data = request.get_json()
        name = data.get('name', 'Anonymous').strip()
        dept = data.get('dept', '-').strip()
        score = float(data.get('score', 0))
        time_sec = int(data.get('time_sec', 0))

        if not name or score is None or time_sec is None:
            return jsonify({"error": "Missing fields"}), 400

        leaderboard = load_leaderboard()
        entry = {
            "name": name,
            "dept": dept,
            "score": score,
            "time_sec": time_sec,
            "time_display": f"{time_sec // 60:02d}:{time_sec % 60:02d}",
            "submitted_at": datetime.utcnow().isoformat()
        }
        leaderboard.append(entry)
        save_leaderboard(leaderboard)

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Submit error: {e}")
        return jsonify({"error": "Server error"}), 500

@app.route('/api/leaderboard')
def get_leaderboard():
    return jsonify(load_leaderboard())

# ──────────────────────────────────────────────
# Server-Sent Events (SSE) for realtime updates
# ──────────────────────────────────────────────
@app.route('/api/events')
def sse_events():
    def generate():
        queue = Queue()
        clients.add(queue)
        try:
            while True:
                data = queue.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            clients.discard(queue)

    return Response(generate(), mimetype='text/event-stream')

def broadcast_update():
    data = json.dumps({"leaderboard": load_leaderboard()})
    for client in list(clients):
        try:
            client.put(data)
        except:
            clients.discard(client)

# Override save to also broadcast
def save_leaderboard():
    with leaderboard_lock:
        try:
            with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
                json.dump(leaderboard, f, ensure_ascii=False, indent=2)
            broadcast_update()
        except Exception as e:
            print(f"Save broadcast error: {e}")

if __name__ == '__main__':
    # For local testing only
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)