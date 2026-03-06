from flask import Flask, render_template, request, jsonify, Response
import json
import os
from datetime import datetime
import threading
from queue import Queue

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# File path & configuration
LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), 'leaderboard.json')
leaderboard_lock = threading.Lock()
leaderboard = []
clients = set()

def load_leaderboard_from_disk():
    """Initial load of the leaderboard from the JSON file."""
    global leaderboard
    if not os.path.exists(LEADERBOARD_FILE):
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
        print(f"Initial load error: {e}")
        leaderboard = []

def save_and_broadcast():
    """Sorts, saves to disk, and pushes updates to all active SSE clients."""
    global leaderboard
    with leaderboard_lock:
        # Final sort before broadcast to ensure correct ranking
        leaderboard.sort(key=lambda x: (-x['score'], x['time_sec']))
        try:
            # Write to JSON
            with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
                json.dump(leaderboard, f, ensure_ascii=False, indent=2)
            
            # Notify all connected clients
            message = json.dumps(leaderboard)
            for client in list(clients):
                try:
                    client.put(message)
                except:
                    clients.discard(client)
        except Exception as e:
            print(f"Broadcast error: {e}")

# Load leaderboard into memory at startup
load_leaderboard_from_disk()

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
    {"q": "রাসূল ﷺ এর সবচেয়ে ছোট ছেলে কে ছিলেন?", "options": ["কাসিম", "আবদুল্লাহ", "ইবরাহিম", "হামজা"], "ans": 2},
    {"q": "রাসূল ﷺ এর দাদার নাম কী?", "options": ["আব্দুল মুত্তালিব", "হাশিম ইবনে আব্দে মানাফ", "আবু তালিব", "আব্বাস ইবনে আব্দুল মুত্তালিব"], "ans": 0},
    {"q": "রাসূল ﷺ কোথায় ইন্তেকাল করেন?", "options": ["মক্কা", "মদিনা", "তাইফ", "দামেস্ক"], "ans": 1},
    {"q": "রাসূল ﷺ কত বছর বয়সে ইন্তেকাল করেন?", "options": ["৬০ বছর", "৬২ বছর", "৬৩ বছর", "৬৫ বছর"], "ans": 2},
    {"q": "রাসূল ﷺ এর উপাধি কী ছিল?", "options": ["আল-আমিন", "আল-ফারুক", "আস-সিদ্দিক", "যুন-নুরাইন"], "ans": 0},
    {"q": "ইসলামের প্রথম খলিফা কে ছিলেন?", "options": ["উমর ইবনে খাত্তাব", "আলী ইবনে আবি তালিব", "আবু বকর", "উসমান ইবনে আফফান"], "ans": 2},
    {"q": "বদর যুদ্ধ কত হিজরিতে হয়েছিল?", "options": ["১ হিজরি", "২ হিজরি", "৩ হিজরি", "৫ হিজরি"], "ans": 1},
    {"q": "মক্কা বিজয় (ফতহ মক্কা) কত হিজরিতে হয়েছিল?", "options": ["৬ হিজরি", "৭ হিজরি", "৮ হিজরি", "৯ হিজরি"], "ans": 2}
]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/questions')
def get_questions():
    return jsonify(QUESTIONS)

@app.route('/api/submit', methods=['POST'])
def submit_score():
    global leaderboard
    try:
        data = request.get_json()
        name = data.get('name', 'Anonymous').strip()
        dept = data.get('dept', '-').strip()
        score = float(data.get('score', 0))
        time_sec = int(data.get('time_sec', 0))

        if not name:
            return jsonify({"error": "Name is required"}), 400

        new_entry = {
            "name": name,
            "dept": dept,
            "score": score,
            "time_sec": time_sec,
            "time_display": f"{time_sec // 60:02d}:{time_sec % 60:02d}",
            "submitted_at": datetime.utcnow().isoformat()
        }
        
        leaderboard.append(new_entry)
        save_and_broadcast() # Instant update triggered here

        return jsonify({"status": "success"})
    except Exception as e:
        print(f"Submission Error: {e}")
        return jsonify({"error": "Failed to save score"}), 500

@app.route('/api/leaderboard')
def get_leaderboard():
    return jsonify(leaderboard)

@app.route('/api/events')
def sse_events():
    """SSE endpoint to push real-time updates to the frontend."""
    def generate():
        q = Queue()
        clients.add(q)
        try:
            # Send current leaderboard immediately upon connection
            yield f"data: {json.dumps(leaderboard)}\n\n"
            while True:
                data = q.get()
                yield f"data: {data}\n\n"
        except GeneratorExit:
            clients.discard(q)

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Note: debug=True can sometimes cause double-loading of SSE in local dev
    app.run(host='0.0.0.0', port=port, debug=False)
