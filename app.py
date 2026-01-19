from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import db, Todo
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# --- DATABASE CONFIGURATION ---
# 1. Get the URL from Render's environment variable
uri = os.environ.get('DATABASE_URL')

if uri:
    # 2. FIX: SQLAlchemy requires 'postgresql://', but Render provides 'postgres://'
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
else:
    # Fallback for local testing
    uri = 'sqlite:///tasks.db'

app.config['SQLALCHEMY_DATABASE_URI'] = uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-placeholder')

# Initialize the database with the app
db.init_app(app)

# --- ROUTES ---
@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        due_date_str = request.form.get('due_date')
        due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
        cat_input = request.form.get('category')
        
        # Use user-defined colors/categories logic
        final_cat = cat_input.strip() if cat_input and cat_input.strip() != "" else "General"

        new_task = Todo(
            title=request.form.get('title'),
            description=request.form.get('description'),
            priority=request.form.get('priority'),
            category=final_cat,
            due_date=due_date_obj
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect('/')

    active_tasks = Todo.query.filter_by(completed=False).all()
    history = Todo.query.filter_by(completed=True).order_by(Todo.date_created.desc()).all()
    
    # Logic for urgency and chart data
    now = datetime.utcnow()
    for task in active_tasks:
        task.is_urgent = False
        if task.due_date:
            diff = task.due_date - now
            task.days_left = diff.days + 1
            if 0 <= task.days_left <= 3:
                task.is_urgent = True

    # Chart logic
    daily_stats = []
    labels = []
    for i in range(6, -1, -1):
        day = (datetime.utcnow() - timedelta(days=i)).date()
        count_on_day = Todo.query.filter(
            Todo.completed == True,
            db.func.date(Todo.date_created) == day
        ).count()
        labels.append(day.strftime('%a')) 
        daily_stats.append(count_on_day)

    return render_template('index.html', 
                           tasks=active_tasks, 
                           history=history, 
                           count=len(history),
                           chart_labels=labels,
                           chart_data=daily_stats)

@app.route('/complete/<int:id>')
def complete(id):
    task = Todo.query.get_or_404(id)
    task.completed = True
    # Reset date_created to the completion time for the chart
    task.date_created = datetime.utcnow()
    db.session.commit()
    return redirect('/')

@app.route('/delete/<int:id>')
def delete(id):
    task = Todo.query.get_or_404(id)
    db.session.delete(task)
    db.session.commit()
    return redirect('/')

# --- INITIALIZATION ---
# This block ensures the 'todo' table is created on the new database immediately
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    # Render uses the PORT environment variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)