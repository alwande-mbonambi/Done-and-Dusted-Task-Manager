import pytest
from app import app, db, Todo

@pytest.fixture
def client():
    #temporary "in-memory" database for testing
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_index_page(client):
    """Proof that the home page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b"DONE & DUSTED" in response.data

def test_add_task(client):
    """Proof that the app can successfully save a task"""
    client.post('/', data={
        'title': 'DevOps Test Task',
        'description': 'Testing the pipeline',
        'priority': 'High',
        'category': 'Work',
        'due_date': '2026-01-01'
    })
    task = Todo.query.filter_by(title='DevOps Test Task').first()
    assert task is not None
    assert task.category == 'Work'

def test_edit_task(client):
    """Proof that editing a task actually updates the database"""
    # Create a task
    client.post('/', data={'title': 'Original Title', 'priority': 'Low'})
    task = Todo.query.filter_by(title='Original Title').first()

    # Send an edit request
    client.post(f'/edit/{task.id}', data={
        'title': 'Updated Title',
        'description': 'New Description',
        'priority': 'High',
        'category': 'Work',
        'due_date': '2026-12-31'
    })

    # Verify the change
    updated_task = Todo.query.get(task.id)
    assert updated_task.title == 'Updated Title'
    assert updated_task.priority == 'High'

def test_complete_task(client):
    """Proof that 'Dusting' a task moves it to history"""
    client.post('/', data={'title': 'Task to Complete'})
    task = Todo.query.filter_by(title='Task to Complete').first()

    # Trigger the completion route
    client.get(f'/complete/{task.id}')

    completed_task = Todo.query.get(task.id)
    assert completed_task.completed is True

def test_delete_task(client):
    """Proof that deleting a task removes it entirely"""
    client.post('/', data={'title': 'Task to Delete'})
    task = Todo.query.filter_by(title='Task to Delete').first()

    # Trigger delete
    client.get(f'/delete/{task.id}')

    deleted_task = Todo.query.get(task.id)
    assert deleted_task is None

def test_bulk_dust_all(client):
    """Proof that selecting multiple tasks and clicking 'DUST ALL' works"""
    # Create two tasks
    client.post('/', data={'title': 'Task 1'})
    client.post('/', data={'title': 'Task 2'})
    task1 = Todo.query.filter_by(title='Task 1').first()
    task2 = Todo.query.filter_by(title='Task 2').first()

    # Simulate Bulk Form submission for "complete"
    client.post('/bulk_action', data={
        'task_ids': [task1.id, task2.id],
        'action': 'complete'
    })

    # Verify both are now in Dusted History
    assert Todo.query.get(task1.id).completed is True
    assert Todo.query.get(task2.id).completed is True

def test_bulk_delete_all(client):
    """Proof that selecting multiple tasks and clicking 'DELETE' removes them"""
    client.post('/', data={'title': 'Delete 1'})
    client.post('/', data={'title': 'Delete 2'})
    t1 = Todo.query.filter_by(title='Delete 1').first()
    t2 = Todo.query.filter_by(title='Delete 2').first()

    # Bulk Form submission for "delete"
    client.post('/bulk_action', data={
        'task_ids': [t1.id, t2.id],
        'action': 'delete'
    })

    # Verify they are gone from the database
    assert Todo.query.get(t1.id) is None
    assert Todo.query.get(t2.id) is None


    
