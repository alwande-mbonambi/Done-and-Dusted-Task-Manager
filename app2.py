from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def simulation():
    # Simulated current_user data
    mock_user = {
        "full_name": "Dev User",
        "username": "DevUser",
        "is_authenticated": True
    }
    return render_template('teams_simulation.html', current_user=mock_user)

if __name__ == '__main__':
    app.run(debug=True, port=5001)