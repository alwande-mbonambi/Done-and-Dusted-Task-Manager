from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# We create the database object here
db = SQLAlchemy()

class Todo(db.Model):
    # Defining columns for our database table
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    priority = db.Column(db.String(20), default='Medium') # Low, Medium, High
    due_date = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

    # This just helps identify the task when we print it
    def __repr__(self):
        return f'<Task {self.id}>'