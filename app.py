import os
import sys
import tempfile
import warnings
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import imagehash
import cv2

warnings.filterwarnings("ignore", category=UserWarning, module="cv2")

# ---- Setup ----
app = Flask(__name__)
app.secret_key = "supersecretkey"  # Required for flash messages
UPLOAD_FOLDER = 'uploads'
DB_FOLDER = 'fungi_database'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_HASH_DIFF = 10

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure folders exist
os.makedirs(DB_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---- Helpers ----
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def compute_image_hash(image_path):
    try:
        with Image.open(image_path) as img:
            return imagehash.average_hash(img)
    except Exception as e:
        print(f"Error: {e}")
        return None

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

# ---- Routes ----
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/identify', methods=['POST'])
def identify():
    if 'image' not in request.files:
        flash('No image file provided.')
        return redirect(url_for('index'))

    file = request.files['image']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)

        plant_db = load_plant_database()
        match, diff = match_plant(upload_path, plant_db)

        if match and diff <= MAX_HASH_DIFF:
            with open(match['text_path'], 'r', encoding='utf-8') as f:
                description = f.read()
            return render_template('result.html',
                                   match_name=match['name'].capitalize(),
                                   match_score=diff,
                                   user_image=url_for('uploaded_file', filename=filename),
                                   match_image=url_for('fungi_image', filename=os.path.basename(match['image_path'])),
                                   description=description)
        else:
            flash("❌ No suitable match found. Try uploading a clearer image.")
            return redirect(url_for('index'))
    else:
        flash("Invalid file format. Only JPG, JPEG, PNG allowed.")
        return redirect(url_for('index'))

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        name = request.form.get('name')
        desc = request.form.get('description')
        file = request.files.get('image')

        if not name or not desc or not file:
            flash('All fields are required.')
            return redirect(url_for('add'))

        if not allowed_file(file.filename):
            flash('Invalid image format.')
            return redirect(url_for('add'))

        filename = f"{secure_filename(name)}.{file.filename.rsplit('.', 1)[1].lower()}"
        image_path = os.path.join(DB_FOLDER, filename)
        text_path = os.path.join(DB_FOLDER, f"{secure_filename(name)}.txt")

        file.save(image_path)
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(desc)

        flash(f"✅ Fungi '{name}' added to the database.")
        return redirect(url_for('index'))

    return render_template('add.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/fungi_images/<filename>')
def fungi_image(filename):
    return send_from_directory(DB_FOLDER, filename)

# ---- Run App ----
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)

