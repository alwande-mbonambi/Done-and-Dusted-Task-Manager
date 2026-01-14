from flask import Flask, render_template, request, redirect
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
        
        # Ensure 'General' is the default if empty
        cat_input = request.form.get('category')
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

@app.route('/edit/<int:id>', methods=['POST'])
def edit_task(id):
    task = Todo.query.get_or_404(id)
    task.title = request.form.get('title')
    task.description = request.form.get('description')
    task.priority = request.form.get('priority')
    
    cat_input = request.form.get('category')
    task.category = cat_input.strip() if cat_input and cat_input.strip() != "" else "General"
    
    due_date_str = request.form.get('due_date')
    task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d') if due_date_str else None
    db.session.commit()
    return redirect('/')

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