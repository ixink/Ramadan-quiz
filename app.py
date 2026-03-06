from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)

# Path to JSON files
LEADERBOARD_FILE = 'leaderboard.json'

# All 21 questions (hardcoded in backend)
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

# Load or initialize leaderboard
def get_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Sort: higher score first, then lower time on tie
            data.sort(key=lambda x: (-x['score'], x['time_sec']))
            return data
    except:
        return []

def save_to_leaderboard(entry):
    leaderboard = get_leaderboard()
    leaderboard.append(entry)
    with open(LEADERBOARD_FILE, 'w', encoding='utf-8') as f:
        json.dump(leaderboard, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/questions')
def api_questions():
    return jsonify(QUESTIONS)

@app.route('/api/submit', methods=['POST'])
def api_submit():
    data = request.get_json()
    
    name = data.get('name', 'Anonymous').strip()
    dept = data.get('dept', '-').strip()
    score = float(data.get('score', 0))
    time_sec = int(data.get('time_sec', 0))

    if not name or score is None or time_sec is None:
        return jsonify({"error": "Missing required fields"}), 400

    entry = {
        "name": name,
        "dept": dept,
        "score": score,
        "time_sec": time_sec,
        "time_display": f"{time_sec // 60:02d}:{time_sec % 60:02d}",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    save_to_leaderboard(entry)

    return jsonify({"status": "success"})

@app.route('/api/leaderboard')
def api_leaderboard():
    return jsonify(get_leaderboard())

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
