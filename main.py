import os
import threading
import time
import secrets
import requests
from flask import Flask, request, send_file, jsonify, session, render_template
import yt_dlp
from user_agent import generate_user_agent

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

downloads_map = {}

def delete_file_later(path, filename, delay=600):
    def task():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
            if filename in downloads_map:
                del downloads_map[filename]
    threading.Thread(target=task).start()

# دالة إرسال المشاهدات/اللايكات من الكود الخاص بك
def send_boost(action_type, video_url):
    token = "FAKETOKEN" # يفضل استخراجه ديناميكياً إذا أمكن
    if action_type == "views":
        api_url = "https://leofame.com/ar/free-tiktok-views?api=1"
        data = {"token": token, "timezone_offset": "Asia/Baghdad", "free_link": video_url, "quantity": "200"}
    else:
        api_url = "https://leofame.com/free-tiktok-likes?api=1"
        data = {"token": token, "timezone_offset": "Asia/Baghdad", "free_link": video_url}

    headers = {
        "User-Agent": generate_user_agent(),
        "Origin": "https://leofame.com",
        "Referer": "https://leofame.com/"
    }

    try:
        r = requests.post(api_url, headers=headers, data=data, timeout=15)
        if r.status_code == 200 and "error" not in r.text.lower() and "wait" not in r.text.lower():
            return True
        return False
    except:
        return False

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    data = request.json
    url = data.get("url")
    action = data.get("action")

    if not url:
        return jsonify({"success": False, "error": "رابط مطلوب"})

    # حالة التحميل
    if action == "download":
        filename = f"video_{int(time.time())}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # خيارات التحميل بدون علامة مائية عبر yt-dlp
        ydl_opts = {
            'outtmpl': filepath,
            'format': 'best',
            'quiet': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            if "id" not in session:
                session["id"] = secrets.token_hex(8)
            
            downloads_map[filename] = session["id"]
            delete_file_later(filepath, filename)
            return jsonify({"success": True, "message": "تم التجهيز، جاري التحميل...", "file": filename})
        except:
            return jsonify({"success": False})

    # حالة المشاهدات واللايكات
    elif action in ["views", "likes"]:
        success = send_boost(action, url)
        if success:
            msg = "تم إرسال المشاهدات بنجاح!" if action == "views" else "تم إرسال اللايكات بنجاح!"
            return jsonify({"success": True, "message": msg})
        else:
            return jsonify({"success": False}) # سيظهر للمستخدم "يرجى المحاولة مرة أخرى"

    return jsonify({"success": False})

@app.route("/get/<filename>")
def get_file(filename):
    user_id = session.get("id")
    if filename in downloads_map and downloads_map[filename] == user_id:
        path = os.path.join(DOWNLOAD_FOLDER, filename)
        if os.path.exists(path):
            return send_file(path, as_attachment=True)
    return "غير مصرح أو الملف انتهت صلاحيته", 403

if __name__ == "__main__":
    app.run(debug=True)
