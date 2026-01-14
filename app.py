from flask import Flask, render_template, request, redirect, url_for
from models import db, Todo
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/', methods=['POST', 'GET'])
def index():
    if request.method == 'POST':
        due_date_str = request.form.get('due_date')
        due_date_obj = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
        
        new_task = Todo(
            title=request.form.get('title'),
            description=request.form.get('description'),
            priority=request.form.get('priority'),
            due_date=due_date_obj,
            completed=False
        )
        db.session.add(new_task)
        db.session.commit()
        return redirect('/')

    # Active tasks and history
    active_tasks = Todo.query.filter_by(completed=False).all()
    history = Todo.query.filter_by(completed=True).order_by(Todo.date_created.desc()).all()
    
    # Calculate Urgency Rule (3 days)
    now = datetime.utcnow()
    for task in active_tasks:
        task.is_urgent = False
        task.days_left = None
        if task.due_date:
            diff = task.due_date - now
            task.days_left = diff.days + 1
            if 0 <= task.days_left <= 3:
                task.is_urgent = True

    return render_template('index.html', tasks=active_tasks, history=history, count=len(history))

@app.route('/complete/<int:id>')
def complete(id):
    task = Todo.query.get_or_404(id)
    task.completed = True
    db.session.commit()
    return redirect('/')

@app.route('/delete/<int:id>')
def delete(id):
    db.session.delete(Todo.query.get_or_404(id))
    db.session.commit()
    return redirect('/')

@app.route('/clear_history')
def clear_history():
    Todo.query.filter_by(completed=True).delete()
    db.session.commit()
    return redirect('/')

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)