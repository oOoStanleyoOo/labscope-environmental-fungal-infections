import os
from flask import Flask, render_template, request, redirect, url_for
from PIL import Image
import imagehash
import tempfile
import shutil

# Configuration
UPLOAD_FOLDER = "uploads"
DB_FOLDER = "fungi_database"
MAX_HASH_DIFF = 10

# Create folders if missing
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(DB_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Helper Functions
def load_plant_database():
    entries = []
    for file in os.listdir(DB_FOLDER):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            name = os.path.splitext(file)[0]
            image_path = os.path.join(DB_FOLDER, file)
            text_path = os.path.join(DB_FOLDER, name + ".txt")
            entries.append({
                'name': name,
                'image_path': image_path,
                'text_path': text_path
            })
    return entries

def compute_image_hash(image_path):
    try:
        with Image.open(image_path) as img:
            return imagehash.average_hash(img)
    except Exception as e:
        print(f"Error: {e}")
        return None

def match_plant(uploaded_image_path, plant_db):
    uploaded_hash = compute_image_hash(uploaded_image_path)
    if uploaded_hash is None:
        return None, None

    closest_match = None
    smallest_diff = float('inf')

    for entry in plant_db:
        db_hash = compute_image_hash(entry['image_path'])
        if db_hash is None:
            continue

        diff = uploaded_hash - db_hash
        if diff < smallest_diff:
            smallest_diff = diff
            closest_match = entry

    return closest_match, smallest_diff

# Routes
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'image' not in request.files:
            return redirect(request.url)

        file = request.files['image']
        if file.filename == '':
            return redirect(request.url)

        if file:
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(temp_path)

            db = load_plant_database()
            match, diff = match_plant(temp_path, db)

            result = {
                "matched": False,
                "match_name": None,
                "description": None,
                "match_image": None,
                "score": diff
            }

            if match and diff <= MAX_HASH_DIFF:
                result['matched'] = True
                result['match_name'] = match['name'].capitalize()
                result['match_image'] = match['image_path']
                if os.path.exists(match['text_path']):
                    with open(match['text_path'], 'r', encoding='utf-8') as f:
                        result['description'] = f.read()

            return render_template("result.html", result=result, uploaded_image=file.filename)

    return render_template('index.html')

@app.route('/about')
def about():
    return "<h2>Fungi Identifier Web App</h2><p>Made with Flask.</p>"

# Start server
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
