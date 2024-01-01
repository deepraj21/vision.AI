import io
import os
import requests
from PIL import Image
from flask import Flask, request, render_template, send_file
from werkzeug.utils import secure_filename 
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import os


app = Flask(__name__)

app.secret_key = 'MYSECRETKEY'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    

def create_tables():
    with app.app_context():
        db.create_all()
        
@app.route('/register', methods=['GET', 'POST'])
def register():
    username = None
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        try:
            user = User(username=username, password=password)
            db.session.add(user)
            db.session.commit()
            session['user_id'] = user.id
            username = user.username
            return render_template('dashboard.html',username=username)
        except IntegrityError:
            db.session.rollback()
            flash('Username already exists. Please choose a different username.', 'error')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    username = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            username = user.username
            return render_template('dashboard.html',username=username)
            
        else:
            flash('Wrong username or password. Please try again.', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('dashboard'))

API_KEY = '581600d1f0720d89963f071cee7a946f7fe6dfd6f73f533ae1aa055600598da7ab3e2531df6c4353fa92610beef6edfc'

def process_image_depth(filename, image_file_object):
    r = requests.post('https://clipdrop-api.co/portrait-depth-estimation/v1',
                      files=
                      {
                          'image_file': ('portrait.jpg', image_file_object, 'image/jpeg'),
                      },
                      headers=
                      {
                          'x-api-key': API_KEY
                      })
    if (r.ok):
        image = Image.open(io.BytesIO(r.content))

        filename_depth = f"static/{filename}_Depth.jpg"
        image.save(filename_depth)
        print(f'Saved Depth Map')
    else:
        r.raise_for_status()

def process_image_normal(filename, image_file_object):
    n = requests.post('https://clipdrop-api.co/portrait-surface-normals/v1',
                      files=
                      {
                          'image_file': ('portrait.jpg', image_file_object, 'image/jpeg'),
                      },
                      headers=
                      {
                          'x-api-key': API_KEY
                      })
    if (n.ok):
        image_n = Image.open(io.BytesIO(n.content))

        filename_normal = f"static/{filename}_Normal.jpg"
        image_n.save(filename_normal)
        print(f'Saved Normal Map')
    else:
        n.raise_for_status()

def upscale_image(filename, image_file_object):
    r = requests.post('https://clipdrop-api.co/image-upscaling/v1/upscale',
                      files={
                          'image_file': (filename, image_file_object, 'image/jpeg'),
                      },
                      data={'target_width': 2048, 'target_height': 2048},
                      headers={
                          'x-api-key': API_KEY
                      })
    if r.ok:
        image = Image.open(io.BytesIO(r.content))

        filename_upscaled = f"static/{filename}_Upscaled.jpg"
        image.save(filename_upscaled)
        print('Saved Upscaled Image')

        return f"{filename}_Upscaled.jpg"
    else:
        r.raise_for_status()
        return None

def generate_sketch_to_image(sketch_image_file_object, prompt):
    r = requests.post('https://clipdrop-api.co/sketch-to-image/v1/sketch-to-image',
                      files={
                          'image_file': ('owl-sketch.jpg', sketch_image_file_object, 'image/jpeg'),
                      },
                      data={
                          'prompt': prompt
                      },
                      headers={
                          'x-api-key': API_KEY
                      })
    if r.ok:
        image = Image.open(io.BytesIO(r.content))

        filename_sketch_to_image = f"static/SketchToImage.jpg"
        image.save(filename_sketch_to_image)
        print('Saved Sketch to Image')
    else:
        r.raise_for_status()

def generate_text_image(prompt):
    r = requests.post('https://clipdrop-api.co/text-to-image/v1',
                      files={
                          'prompt': (None, prompt, 'text/plain')
                      },
                      headers={
                          'x-api-key': API_KEY
                      })
    if r.ok:
        image = Image.open(io.BytesIO(r.content))

        filename_text_image = f"static/TextImage.jpg"
        image.save(filename_text_image)
        print('Saved Text Image')
    else:
        r.raise_for_status()

# @app.route('/', methods=['GET', 'POST'])
# def index():
#     return render_template('index.html')

@app.route('/',methods=['GET','POST'])
def dashboard():
    username = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        username = user.username
        
        return render_template('dashboard.html', username=username)
    
    return render_template('dashboard.html')


@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    return send_file(filename, as_attachment=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg', 'jpeg'}

@app.route('/depth_image',methods=['GET','POST'])
def depthImage():
    depth_image_filename = None
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_file_object = file.read()

            process_image_depth(filename, image_file_object)
            
            depth_image_filename = f"{filename}_Depth.jpg"
    
    return render_template('depth.html', depth_image_filename=depth_image_filename)

@app.route('/normal_image',methods=['GET','POST'])
def normalImage():
    normal_image_filename = None
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_file_object = file.read()

            process_image_normal(filename, image_file_object)
            
            normal_image_filename = f"{filename}_Normal.jpg"
    
    return render_template('normal.html', normal_image_filename=normal_image_filename)

@app.route('/text_to_image', methods=['GET', 'POST'])
def textImage():
    text_image_filename = None
    if request.method == 'POST':
        prompt = request.form.get('prompt')
        if prompt:
            r = requests.post('https://clipdrop-api.co/text-to-image/v1',
                              files={
                                  'prompt': (None, prompt, 'text/plain')
                              },
                              headers={
                                  'x-api-key': API_KEY
                              })
            if r.ok:
                image = Image.open(io.BytesIO(r.content))

                filename_text_image = f"static/TextImage.jpg"
                image.save(filename_text_image)
                print('Saved Text Image')

                text_image_filename = "TextImage.jpg"
            else:
                r.raise_for_status()

    return render_template('text_to_image.html', text_image_filename=text_image_filename)

@app.route('/sketch_to_image', methods=['GET', 'POST'])
def sketchToImage():
    sketch_to_image_filename = None
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            sketch_image_file_object = file.read()
            prompt = request.form.get('prompt')

            if prompt:
                generate_sketch_to_image(sketch_image_file_object, prompt)
                sketch_to_image_filename = "SketchToImage.jpg"

    return render_template('sketch_to_image.html', sketch_to_image_filename=sketch_to_image_filename)


@app.route('/image_upscale', methods=['GET', 'POST'])
def imageUpscale():
    upscaled_image_filename = None
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_file_object = file.read()

            upscaled_image_filename = upscale_image(filename, image_file_object)

    return render_template('image_upscale.html', upscaled_image_filename=upscaled_image_filename)

@app.route('/inpainting', methods=['GET', 'POST'])
def inpainting():
    inpainted_image_filename = None
    if request.method == 'POST':
        file = request.files['image']
        mask_file = request.files['mask']
        if file and allowed_file(file.filename) and mask_file and allowed_file(mask_file.filename):
            filename = secure_filename(file.filename)
            image_file_object = file.read()
            mask_file_object = mask_file.read()

            r = requests.post('https://clipdrop-api.co/cleanup/v1',
                              files={
                                  'image_file': ('image.jpg', image_file_object, 'image/jpeg'),
                                  'mask_file': ('mask.png', mask_file_object, 'image/png')
                              },
                              headers={'x-api-key': API_KEY})
            if r.ok:
                image = Image.open(io.BytesIO(r.content))
                filename_inpainted = f"static/{filename}_Inpainted.jpg"
                image.save(filename_inpainted)
                inpainted_image_filename = f"{filename}_Inpainted.jpg"
            else:
                r.raise_for_status()

    return render_template('inpainting.html', inpainted_image_filename=inpainted_image_filename)

@app.route('/remove_background', methods=['GET', 'POST'])
def remove_background():
    bg_removed_image_filename = None
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_file_object = file.read()

            r = requests.post('https://clipdrop-api.co/remove-background/v1',
                              files={
                                  'image_file': ('image.jpg', image_file_object, 'image/jpeg'),
                              },
                              headers={'x-api-key': API_KEY})
            if r.ok:
                image = Image.open(io.BytesIO(r.content))
                filename_bg_removed = f"static/{filename}_BGRemoved.jpg"
                image.save(filename_bg_removed)
                bg_removed_image_filename = f"{filename}_BGRemoved.jpg"
            else:
                r.raise_for_status()

    return render_template('remove_background.html', bg_removed_image_filename=bg_removed_image_filename)

@app.route('/reimagine', methods=['GET', 'POST'])
def reimagine():
    reimagine_image_filename = None
    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_file_object = file.read()

            r = requests.post('https://clipdrop-api.co/reimagine/v1/reimagine',
                              files={
                                  'image_file': ('image.jpg', image_file_object, 'image/jpeg'),
                              },
                              headers={'x-api-key': API_KEY})
            if r.ok:
                image = Image.open(io.BytesIO(r.content))
                filename_reimagine = f"static/{filename}_Reimagined.jpg"
                image.save(filename_reimagine)
                reimagine_image_filename = f"{filename}_Reimagined.jpg"
            else:
                r.raise_for_status()

    return render_template('reimagine.html', reimagine_image_filename=reimagine_image_filename)


if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
