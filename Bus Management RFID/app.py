import datetime
from flask import Flask, jsonify, request, redirect, url_for, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_cors import CORS
import heapq  # For Dijkstra's algorithm

app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(256), nullable=False)

# Bus Model
class Bus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(50), unique=True)
    route = db.Column(db.String(100))
    capacity = db.Column(db.Integer)

# RFID Reading Model
class RFIDReading(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(50))
    rfid_tag = db.Column(db.String(50))
    timestamp = db.Column(db.String(100))


    
# Optimized Route Model
class OptimizedRoute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bus_number = db.Column(db.String(50))
    optimized_route = db.Column(db.String(255))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize database
with app.app_context():
    db.create_all()

# Simple Dijkstra's algorithm for route optimization
def dijkstra(graph, start, end):
    queue = [(0, start, [])]
    visited = set()
    while queue:
        (cost, node, path) = heapq.heappop(queue)
        if node in visited:
            continue
        path = path + [node]
        if node == end:
            return (cost, path)
        visited.add(node)
        for (next_node, weight) in graph[node]:
            heapq.heappush(queue, (cost + weight, next_node, path))
    return float("inf"), []

# Example Graph (Hardcoded for demonstration)
graph = {
    'A': [('B', 1), ('C', 4)],
    'B': [('A', 1), ('C', 2), ('D', 5)],
    'C': [('A', 4), ('B', 2), ('D', 1)],
    'D': [('B', 5), ('C', 1)]
}

# Home Route to redirect to login or dashboard
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Please log in.")
        return redirect(url_for('login'))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Login failed. Check your credentials and try again.")
    
    return render_template('login.html')

# Logout Route
@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Dashboard Route (only accessible if logged in)
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user)

# Register Bus Route
@app.route('/register_bus', methods=['POST'])
@login_required
def register_bus():
    data = request.get_json()
    new_bus = Bus(bus_number=data['bus_number'], route=data['route'], capacity=data.get('capacity'))
    db.session.add(new_bus)
    db.session.commit()
    return jsonify({"message": "Bus successfully registered"}), 200

# Get Buses Route
@app.route('/get_buses', methods=['GET'])
@login_required
def get_buses():
    buses = Bus.query.all()
    bus_list = [{"bus_number": bus.bus_number, "route": bus.route, "capacity": bus.capacity} for bus in buses]
    return jsonify(bus_list), 200


@app.route('/rfid_scan', methods=['POST'])
def rfid_scan():
    data = request.get_json()
    print(f"Received data: {data}")  # Debugging print statement
    bus_number = data.get('bus_number')
    rfid_tag = data.get('rfid_tag')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if bus_number and rfid_tag:
        new_reading = RFIDReading(bus_number=bus_number, rfid_tag=rfid_tag, timestamp=timestamp)
        db.session.add(new_reading)
        db.session.commit()
        print(f"Data saved to database: Bus Number={bus_number}, RFID Tag={rfid_tag}, Timestamp={timestamp}")
        return jsonify({"message": "RFID scan successfully recorded"}), 200
    else:
        print("Invalid data received")
        return jsonify({"message": "Invalid data received"}), 400

@app.route('/rfid_table')
def rfid_table():
    readings = RFIDReading.query.all()
    return render_template('rfid_table.html', readings=readings)

# @app.route('/')
# def index():
#     return redirect(url_for('rfid_table'))

# Get RFID Readings Route
@app.route('/get_rfid_readings/<bus_number>', methods=['GET'])
@login_required
def get_rfid_readings(bus_number):
    readings = RFIDReading.query.filter_by(bus_number=bus_number).all()
    readings_list = [
        {
            'bus_number': reading.bus_number,
            'rfid_tag': reading.rfid_tag,
            'timestamp': reading.timestamp
        }
        for reading in readings
    ]
    return jsonify(readings_list), 200

# AI Route Optimization API
@app.route('/optimize_route/<bus_number>', methods=['GET'])
@login_required
def optimize_route(bus_number):
    start = 'A'  # Example start
    end = 'D'    # Example end
    cost, optimized_path = dijkstra(graph, start, end)
    optimized_route_str = ' -> '.join(optimized_path)
    
    # Store optimized route in the database
    existing_route = OptimizedRoute.query.filter_by(bus_number=bus_number).first()
    if existing_route:
        existing_route.optimized_route = optimized_route_str
    else:
        new_route = OptimizedRoute(bus_number=bus_number, optimized_route=optimized_route_str)
        db.session.add(new_route)
    db.session.commit()

    return jsonify({
        "bus_number": bus_number,
        "optimized_route": optimized_route_str,
        "total_cost": cost
    }), 200

# Get All Optimized Routes API
@app.route('/get_optimized_routes', methods=['GET'])
@login_required
def get_optimized_routes():
    routes = OptimizedRoute.query.all()
    routes_list = [{"bus_number": route.bus_number, "optimized_route": route.optimized_route} for route in routes]
    return jsonify(routes_list), 200

# Data Visualization API
@app.route('/visualization', methods=['GET'])
@login_required
def data_visualization():
    total_users = User.query.count()
    total_buses = Bus.query.count()
    total_rfid_numbers = RFIDReading.query.count()

    history = []
    for user in User.query.all():
        user_history = {
            "username": user.username,
            "email": user.email,
            "rfid_number": None,
            "bus_number": None,
            "route": None,
            "capacity": None
        }
        for reading in RFIDReading.query.filter_by(rfid_tag=user.email).all():
            user_history["rfid_number"] = reading.rfid_tag
            bus = Bus.query.filter_by(bus_number=reading.bus_number).first()
            if bus:
                user_history["bus_number"] = bus.bus_number
                user_history["route"] = bus.route
                user_history["capacity"] = bus.capacity
        history.append(user_history)

    return jsonify({
        "total_users": total_users,
        "total_buses": total_buses,
        "total_rfid_numbers": total_rfid_numbers,
        "history": history
    }), 200

if __name__ == '__main__':
    # Ensure the application context is available
    with app.app_context():
        db.create_all()

    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)