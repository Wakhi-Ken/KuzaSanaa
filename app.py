from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
import os
from sqlalchemy.orm import joinedload  # For eager loading related data

app = Flask(__name__)
app.secret_key = '05f3477f588134db3e689a77dc84cdfe'  # Secret for sessions & security
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kuzasanaa.db'  # SQLite DB file
app.config['UPLOAD_FOLDER'] = 'static/uploads'  # Where uploaded files go

# Setup the database object for ORM
db = SQLAlchemy(app)

# -------------- Database Models ----------------
class User(db.Model):
    UserID = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(80), nullable=False)
    Email = db.Column(db.String(120), unique=True, nullable=False)
    Password = db.Column(db.String(200), nullable=False)
    Role = db.Column(db.String(20), nullable=False)
    Bio = db.Column(db.String(500))  # User bio/profile description
    comments = db.relationship('Comment', backref='author', lazy=True)  # Link to comments by user

class Content(db.Model):
    ContentID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID'), nullable=False)
    FilePath = db.Column(db.String(200), nullable=False)  # Filename/path of uploaded file
    UploadDate = db.Column(db.DateTime, default=datetime.utcnow)  # Timestamp upload happened
    user = db.relationship('User', backref='contents')  # Connect back to uploader

class Comment(db.Model):
    CommentID = db.Column(db.Integer, primary_key=True)
    ContentID = db.Column(db.Integer, db.ForeignKey('content.ContentID'), nullable=False)
    UserID = db.Column(db.Integer, db.ForeignKey('user.UserID'), nullable=False)
    CommentText = db.Column(db.Text, nullable=False)
    CommentDate = db.Column(db.DateTime, default=datetime.utcnow)  # When comment was made
    user = db.relationship('User')  # User who made the comment

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # e.g. podcast, campaign
    media_type = db.Column(db.String(20), nullable=False)  # type like audio, video, etc
    file_path = db.Column(db.String(200), nullable=False)  # actual file location
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.UserID'), nullable=False)
    uploader = db.relationship('User')  # Link to who uploaded this media

# -------------- Context Processor ----------------
@app.context_processor
def inject_now():
    # Makes current UTC time and logged in user id available globally in templates
    return {
        'now': datetime.utcnow(),
        'current_user_id': session.get('user_id')
    }

# -------------- Routes ----------------
@app.route('/initdb')
def init_db():
    # Quick helper to create tables (for dev/testing)
    db.create_all()
    return "Database initialized!"

@app.route('/')
def index():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    username = user.Username if user else 'Guest'

    # Grab all content, newest first
    contents = Content.query.order_by(Content.UploadDate.desc()).all()

    # For each content, load its comments (sorted oldest first)
    for content in contents:
        content.comments = Comment.query.filter_by(ContentID=content.ContentID).order_by(Comment.CommentDate).all()

    # Render homepage with user info and uploads
    return render_template('index.html', username=username, contents=contents)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Create a new user from form data
        new_user = User(
            Username=request.form['username'],
            Email=request.form['email'],
            Password=request.form['password'],  # Note: no hashing here — consider adding it
            Role=request.form['role']
        )
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.UserID  # Log them in right away
        flash("Registration successful! Please complete your profile.")
        return redirect(url_for('profile'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Look up user by username and password
        user = User.query.filter_by(Username=request.form['username'], Password=request.form['password']).first()

        if user:
            session['user_id'] = user.UserID
            flash("Login successful!")
            return redirect(url_for('index'))
        flash("Invalid username or password.")

    return render_template('login.html')

@app.route('/logout')
def logout():
    # Remove user id from session to log out
    session.pop('user_id', None)
    flash("You have been logged out.")
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if request.method == 'POST':
        bio = request.form.get('bio')
        if bio:
            user.Bio = bio  # Update bio field
            db.session.commit()
            flash("Bio updated successfully!")
        return redirect(url_for('profile'))

    # Get all uploads by this user
    uploads = Content.query.filter_by(UserID=user_id).all()
    return render_template('profile.html', user=user, user_uploads=uploads)

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'user_id' not in session:
        flash("Login required to upload files.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        file = request.files.get('file')

        # Simple validation for file selection
        if not file or file.filename == '':
            flash("No selected file")
            return redirect(request.url)

        # Secure the filename and save it
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Create content record pointing to uploaded file
        db.session.add(Content(UserID=session['user_id'], FilePath=filename))
        db.session.commit()
        flash("File uploaded successfully!")
        return redirect(url_for('index'))

    return render_template('upload.html')

@app.route('/upload_media', methods=['GET', 'POST'])
def upload_media():
    if 'user_id' not in session:
        flash("Login required.")
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Grab form data
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        media_type = request.form['media_type']
        file = request.files['file']

        # Check required fields
        if not all([title, category, media_type, file]):
            flash("All fields are required.")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Save new media record
        media = Media(
            title=title,
            description=description,
            category=category,
            media_type=media_type,
            file_path=filename,
            user_id=session['user_id']
        )
        db.session.add(media)
        db.session.commit()
        flash("Media uploaded.")
        return redirect(url_for('index'))

    return render_template('upload_media.html')

@app.route('/comment/<int:content_id>', methods=['POST'])
def add_comment(content_id):
    if 'user_id' not in session:
        flash("Login to comment.")
        return redirect(url_for('login'))

    comment_text = request.form.get('comment_text')
    if comment_text:
        db.session.add(Comment(ContentID=content_id, UserID=session['user_id'], CommentText=comment_text))
        db.session.commit()
        flash("Comment added!")
    return redirect(url_for('index'))

@app.route('/edit_comment/<int:comment_id>', methods=['POST'])
def edit_comment(comment_id):
    comment = Comment.query.get(comment_id)

    # Allow edit only if comment belongs to user and within 30 seconds of posting
    if comment and comment.UserID == session.get('user_id'):
        if (datetime.utcnow() - comment.CommentDate).total_seconds() <= 30:
            new_text = request.form.get('comment_text')
            if new_text:
                comment.CommentText = new_text
                db.session.commit()
                flash("Comment updated.")
        else:
            flash("Edit window expired.")
    else:
        flash("Unauthorized.")

    return redirect(url_for('index'))

@app.route('/delete/<int:content_id>', methods=['POST'])
def delete_upload(content_id):
    user_id = session.get('user_id')
    content = Content.query.get(content_id)

    # Only uploader can delete their upload
    if content and content.UserID == user_id:
        # Remove file from filesystem
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], content.FilePath))
        db.session.delete(content)
        db.session.commit()
        flash("Upload deleted.")
    else:
        flash("Unauthorized or not found.")
    return redirect(url_for('profile'))

@app.route('/user/<int:user_id>')
def public_profile(user_id):
    # Show public profile page of any user by id
    user = User.query.get_or_404(user_id)
    uploads = Content.query.filter_by(UserID=user_id).order_by(Content.UploadDate.desc()).all()
    return render_template('public_profile.html', user=user, uploads=uploads)

@app.route('/search')
def search():
    if 'user_id' not in session:
        flash("Login to search.")
        return redirect(url_for('login'))

    query = request.args.get('q', '').strip()
    if not query:
        flash("Enter a search term.")
        return redirect(url_for('index'))

    # Search users by username or role
    users = User.query.filter((User.Username.ilike(f'%{query}%')) | (User.Role.ilike(f'%{query}%'))).all()

    # Search uploads by filename or uploader matching found users
    uploads = Content.query.filter((Content.FilePath.ilike(f'%{query}%')) | (Content.UserID.in_([u.UserID for u in users]))).all()

    # Attach user info to uploads
    for u in uploads:
        u.user = User.query.get(u.UserID)

    return render_template('search_results.html', query=query, users=users, uploads=uploads)

# -------------- Campaigns and Media Filters ---------------
@app.route('/campaigns')
def campaigns():
    # Roles eligible for campaigns
    campaign_roles = [
        "Cultural Strategist",
        "Cultural Ambassador",
        "Tourism Promoter",
        "Digital Campaign Manager",
        "Exhibition Curator",
        "Event Organizer",
        "Cultural Educator",
        "Community Organizer",
        "Supporter",
        "Enthusiast",
    ]

    # Get media tagged as campaign, with uploader loaded
    campaigns = Media.query.options(joinedload(Media.uploader))\
        .filter_by(category='campaign')\
        .order_by(Media.upload_date.desc())\
        .all()

    # Filter campaigns to only include uploaders with desired roles
    filtered_campaigns = [item for item in campaigns if item.uploader and item.uploader.Role in campaign_roles]

    return render_template('campaigns.html', campaigns=filtered_campaigns)

@app.route('/media')
def podcast_docs():
    # Roles for podcasts/docs filtering
    podcast_roles = [
        "Documentary Producer",
        "Podcast Host",
        "Storyteller",
        "Artist",
        "Visual Designer",
        "Crafts Maker",
        "Performer",
        "Traditional Dancer",
        "Content Creator",
    ]

    # Fetch podcasts and documentaries with uploader data
    media = Media.query.options(joinedload(Media.uploader))\
        .filter(Media.category.in_(['podcast', 'documentary']))\
        .order_by(Media.upload_date.desc())\
        .all()

    # Filter media to only those with uploader in specified roles
    filtered_media = [item for item in media if item.uploader and item.uploader.Role in podcast_roles]

    return render_template('podcast_docs.html', media=filtered_media)

# ------------- Auto-create DB tables on app start (dev only) -------------
with app.app_context():
    db.create_all()

# ------------------ Run App ------------------
if __name__ == '__main__':
    app.run(debug=True)
