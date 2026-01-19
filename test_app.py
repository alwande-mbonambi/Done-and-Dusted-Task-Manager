import pytest
from app import app, db, Todo

@pytest.fixture
def client():
    """Sets up a temporary 'in-memory' database for testing."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_index_page_loads(client):
    """Proof that the home page loads correctly and title is present."""
    response = client.get('/')
    assert response.status_code == 200
    assert b"DONE & DUSTED" in response.data

def test_add_and_edit_task(client):
    """Proof that tasks can be created and later updated."""
    client.post('/', data={
        'title': 'Test Task',
        'description': 'DevOps proof',
        'priority': 'High',
        'category': 'Work'
    })
    task = Todo.query.filter_by(title='Test Task').first()
    assert task is not None

    client.post(f'/edit/{task.id}', data={
        'title': 'Updated Task',
        'description': 'Updated description',
        'priority': 'Low',
        'category': 'Home'
    })
    db.session.expire_all() # Refresh the database state
    updated_task = Todo.query.get(task.id)
    assert updated_task.title == 'Updated Task'

def test_task_movement_to_history(client):
    """Proof of History: Verifies an active task moves to history when completed."""
    client.post('/', data={'title': 'Move to History'})
    task = Todo.query.filter_by(title='Move to History').first()
    
    # Complete the task
    client.get(f'/complete/{task.id}')
    
    db.session.expire_all()
    updated_task = Todo.query.get(task.id)
    # Check the database flag directly for absolute proof
    assert updated_task.completed is True

def test_bulk_dust_all(client):
    """Proof that selecting multiple tasks and using 'DUST ALL' works."""
    client.post('/', data={'title': 'Bulk 1'})
    client.post('/', data={'title': 'Bulk 2'})
    t1 = Todo.query.filter_by(title='Bulk 1').first()
    t2 = Todo.query.filter_by(title='Bulk 2').first()

    client.post('/bulk_action', data={'task_ids': [t1.id, t2.id], 'action': 'complete'})
    
    db.session.expire_all()
    assert Todo.query.get(t1.id).completed is True
    assert Todo.query.get(t2.id).completed is True

def test_bulk_delete_all(client):
    """Proof that selecting multiple tasks and using 'DELETE' removes them."""
    client.post('/', data={'title': 'Delete 1'})
    client.post('/', data={'title': 'Delete 2'})
    t1 = Todo.query.filter_by(title='Delete 1').first()
    t2 = Todo.query.filter_by(title='Delete 2').first()

    client.post('/bulk_action', data={'task_ids': [t1.id, t2.id], 'action': 'delete'})
    
    db.session.expire_all()
    assert Todo.query.get(t1.id) is None
    assert Todo.query.get(t2.id) is None

def test_single_delete(client):
    """Proof that the individual delete button (X) works."""
    client.post('/', data={'title': 'Single Delete'})
    task = Todo.query.filter_by(title='Single Delete').first()
    client.get(f'/delete/{task.id}')
    
    db.session.expire_all()
    assert Todo.query.get(task.id) is None