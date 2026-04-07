import os
import threading
import time
import secrets
from flask import Flask, request, send_file, jsonify, session, render_template
import yt_dlp

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
            print(f" تم حذف: {filename}")
        if filename in downloads_map:
            del downloads_map[filename]

    threading.Thread(target=task).start()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/download", methods=["POST"])
def download():
    data = request.json
    url = data.get("url")

    if not url:
        return jsonify({"error": "رابط غير صالح"}), 400

    filename = f"video_{int(time.time())}.mp4"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    ydl_opts = {
        'outtmpl': filepath,
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if "id" not in session:
            session["id"] = secrets.token_hex(8)

        user_id = session["id"]
        downloads_map[filename] = user_id

        delete_file_later(filepath, filename)

        return jsonify({"success": True, "file": filename})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/get/<filename>")
def get_file(filename):
    user_id = session.get("id")

    if filename not in downloads_map:
        return "غير مصرح", 403

    if downloads_map[filename] != user_id:
        return "غير مصرح", 403

    path = os.path.join(DOWNLOAD_FOLDER, filename)

    if os.path.exists(path):
        return send_file(path, as_attachment=False) # تم تغييرها لتعرض في المتصفح

    return "الملف غير موجود", 404


if __name__ == "__main__":
    app.run(debug=True)
