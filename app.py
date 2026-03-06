# app.py
from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import os
from datetime import datetime
import threading

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# File paths
LEADERBOARD_FILE = os.path.join(os.path.dirname(__file__), 'leaderboard.json')

# Thread lock to prevent race conditions on JSON writes
leaderboard_lock = threading.Lock()

# All 21 questions (hardcoded)
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

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Sort: highest score first, then lowest time on tie
            data.sort(key=lambda x: (-x['score'], x['time_sec']))
            return data
    except Exception as e:
        print(f"Leaderboard load error: {e}")
        return []

def save_leaderboard(data):
    with leaderboard_lock:
        try:
            with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Leaderboard save error: {e}")

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
            return jsonify({"error": "Missing required fields"}), 400

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
def get_leaderboard_api():
    return jsonify(load_leaderboard())

# Optional: serve static files explicitly (helps debugging)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # Local development only
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)