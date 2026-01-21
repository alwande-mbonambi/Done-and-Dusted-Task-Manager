from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Todo, User
from datetime import datetime, timedelta
import os
import re

app = Flask(__name__)

# Config
uri = os.environ.get('DATABASE_URL')
if uri and uri.startswith("postgres://"):
    uri = uri.replace("postgres://", "postgresql://", 1)
else:
    uri = 'sqlite:///tasks.db'

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-secret')

db.init_app(app)

# Login Manager Setup
login_manager = LoginManager()
login_manager.login_view = 'auth'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- HELPER ROUTES FOR VALIDATION ---
@app.route('/check_uniqueness', methods=['POST'])
def check_uniqueness():
    data = request.get_json()
    field = data.get('field')
    value = data.get('value')
    
    if field == 'username':
        exists = User.query.filter_by(username=value).first() is not None
        return jsonify({'exists': exists})
    elif field == 'email':
        exists = User.query.filter_by(email=value).first() is not None
        return jsonify({'exists': exists})
    return jsonify({'exists': False})

# --- MAIN ROUTES ---

@app.route('/', methods=['POST', 'GET'])
def index():
    # If POST (Adding Task), ensure user is logged in
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('auth'))

        # Handle Date and Time
        due_date_str = request.form.get('due_date')
        due_date_obj = None
        if due_date_str:
            try:
                # Expecting format 'YYYY-MM-DDTHH:MM' from datetime-local input
                due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                # Fallback if seconds are included or format varies
                try:
                    due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d')
                except:
                    due_date_obj = None

        cat_input = request.form.get('category')
        final_cat = cat_input.strip() if cat_input and cat_input.strip() != "" else "General"

        new_task = Todo(
            title=request.form.get('title'),
            description=request.form.get('description'),
            priority=request.form.get('priority'),
            category=final_cat,
            due_date=due_date_obj,
            user_id=current_user.id
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect('/')

    # GET Logic
    existing_categories = []
    
    if current_user.is_authenticated:
        active_tasks = Todo.query.filter_by(user_id=current_user.id, completed=False).all()
        history = Todo.query.filter_by(user_id=current_user.id, completed=True).order_by(Todo.date_created.desc()).all()
        
        # Get unique categories for dropdown
        cats = db.session.query(Todo.category).filter_by(user_id=current_user.id).distinct().all()
        existing_categories = [c[0] for c in cats if c[0]]
    else:
        active_tasks = []
        history = []

    # Priority, Urgency and Chart Logic
    now = datetime.now() # Use local server time or utc depending on pref, aligning with datetime-local
    
    for task in active_tasks:
        task.is_urgent = False
        task.is_overdue = False
        task.is_upcoming = False
        
        if task.due_date:
            diff = task.due_date - now
            total_seconds = diff.total_seconds()
            
            # Logic: If Overdue or < 24 hours, force Priority Display to High
            if total_seconds < 0:
                task.is_overdue = True
                task.priority = 'High' # Force high priority for display/sort
            elif total_seconds < 86400: # Less than 24 hours
                task.is_upcoming = True # Orange state
                task.priority = 'High' # Force high priority

            task.days_left = diff.days

    daily_stats = []
    labels = []
    if current_user.is_authenticated:
        for i in range(6, -1, -1):
            day = (datetime.utcnow() - timedelta(days=i)).date()
            count_on_day = Todo.query.filter(
                Todo.user_id == current_user.id,
                Todo.completed == True,
                db.func.date(Todo.date_created) == day
            ).count()
            labels.append(day.strftime('%a')) 
            daily_stats.append(count_on_day)
    else:
        labels = [(datetime.utcnow() - timedelta(days=i)).strftime('%a') for i in range(6, -1, -1)]
        daily_stats = [0]*7

    return render_template('index.html', 
                           tasks=active_tasks, 
                           history=history, 
                           count=len(history),
                           existing_categories=existing_categories,
                           chart_labels=labels,
                           chart_data=daily_stats)

@app.route('/auth')
def auth():
    return render_template('authentication.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        login_user(user)
        return redirect(url_for('index'))
    else:
        flash('Invalid credentials, please try again.', 'error')
        return redirect(url_for('auth'))

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    email = request.form.get('email')
    password = request.form.get('password')
    full_name = request.form.get('full_name')

    # Backend Validation as safety net
    if not re.match("^[a-z0-9_]+$", username):
        flash('Username invalid (lowercase, numbers, _ only).', 'error')
        return redirect(url_for('auth'))

    if User.query.filter_by(email=email).first():
        flash('Email already exists.', 'error')
        return redirect(url_for('auth'))
    
    if User.query.filter_by(username=username).first():
        flash('Username already exists.', 'error')
        return redirect(url_for('auth'))

    new_user = User(
        username=username, 
        email=email, 
        password=generate_password_hash(password, method='scrypt'),
        full_name=full_name
    )
    db.session.add(new_user)
    db.session.commit()
    
    login_user(new_user)
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    new_email = request.form.get('email')
    new_password = request.form.get('password')
    new_name = request.form.get('full_name')

    # Unique check for email if changed
    if new_email and new_email != current_user.email:
        if User.query.filter_by(email=new_email).first():
            flash('Email already in use by another account.', 'error')
            return redirect(url_for('index'))
        current_user.email = new_email
        
    if new_name:
        current_user.full_name = new_name

    if new_password:
        # Enforce basic strength check on update too
        if len(new_password) < 6:
            flash('Password too weak.', 'error')
            return redirect(url_for('index'))
        current_user.password = generate_password_hash(new_password, method='scrypt')
    
    db.session.commit()
    flash('Profile updated successfully!', 'success')
    return redirect(url_for('index'))

# --- EXISTING TASK ROUTES (Protected) ---

@app.route('/edit/<int:id>', methods=['POST'])
@login_required
def edit_task(id):
    task = Todo.query.get_or_404(id)
    if task.user_id != current_user.id: return redirect('/')
    
    task.title = request.form.get('title')
    task.description = request.form.get('description')
    task.priority = request.form.get('priority')
    
    cat_input = request.form.get('category')
    task.category = cat_input.strip() if cat_input and cat_input.strip() != "" else "General"
    
    due_date_str = request.form.get('due_date')
    if due_date_str and due_date_str.strip() != "":
         try:
            task.due_date = datetime.strptime(due_date_str, '%Y-%m-%dT%H:%M')
         except:
             # Fallback
             task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d')
    else:
        task.due_date = None
        
    db.session.commit()
    return redirect('/')

@app.route('/bulk_action', methods=['POST'])
@login_required
def bulk_action():
    task_ids = request.form.getlist('task_ids')
    action = request.form.get('action')
    if not task_ids: return redirect('/')
        
    tasks = Todo.query.filter(Todo.id.in_(task_ids), Todo.user_id == current_user.id).all()
    
    if action == 'complete':
        for task in tasks:
            task.completed = True
            task.date_created = datetime.utcnow()
    elif action == 'delete':
        for task in tasks:
            db.session.delete(task)
            
    db.session.commit()
    return redirect('/')

@app.route('/complete/<int:id>')
@login_required
def complete(id):
    task = Todo.query.get_or_404(id)
    if task.user_id == current_user.id:
        task.completed = True
        task.date_created = datetime.utcnow()
        db.session.commit()
    return redirect('/')

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    task = Todo.query.get_or_404(id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect('/')

@app.route('/clear_history')
@login_required
def clear_history():
    Todo.query.filter_by(user_id=current_user.id, completed=True).delete()
    db.session.commit()
    return redirect('/')

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    flash('Recovery link sent (Simulated)', 'success')
    return redirect(url_for('auth'))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)