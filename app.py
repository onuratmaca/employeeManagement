from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)

class ClockLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    clock_in = db.Column(db.DateTime, nullable=True)
    clock_out = db.Column(db.DateTime, nullable=True)

# Initialize Database
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def home():
    return "Employee Management System is Live! Navigate to /login or other routes."


@app.route('/register', methods=['POST'])
def register():
    data = request.json
    if User.query.filter_by(username=data['username']).first():
        return jsonify({"status": "fail", "message": "User already exists"}), 400
    user = User(username=data['username'], password=data['password'], is_admin=False)
    db.session.add(user)
    db.session.commit()
    return jsonify({"status": "success", "message": "Registration successful, pending approval"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username'], password=data['password']).first()
    if user and user.is_approved:
        return jsonify({"status": "success", "message": "Login successful"}), 200
    elif user and not user.is_approved:
        return jsonify({"status": "fail", "message": "User not approved yet"}), 403
    return jsonify({"status": "fail", "message": "Invalid credentials"}), 401

@app.route('/unapproved-users', methods=['GET'])
def unapproved_users():
    admin_username = request.args.get("admin_username")
    admin = User.query.filter_by(username=admin_username, is_admin=True).first()
    if admin:
        unapproved = User.query.filter_by(is_approved=False).all()
        return jsonify([{"id": user.id, "username": user.username} for user in unapproved]), 200
    return jsonify({"status": "fail", "message": "Not authorized"}), 403

@app.route('/approve-user', methods=['POST'])
def approve_user():
    data = request.json
    admin_username = data.get('admin_username')
    admin = User.query.filter_by(username=admin_username, is_admin=True).first()
    user = User.query.filter_by(username=data['username']).first()
    if admin and user:
        user.is_approved = True
        db.session.commit()
        return jsonify({"status": "success", "message": "User approved"}), 200
    return jsonify({"status": "fail", "message": "Approval failed"}), 400

@app.route('/clock-in', methods=['POST'])
def clock_in():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user:
        clock_log = ClockLog(user_id=user.id, clock_in=datetime.now())
        db.session.add(clock_log)
        db.session.commit()
        return jsonify({"status": "success", "message": "Clock-in successful"}), 200
    return jsonify({"status": "fail", "message": "User not found"}), 404

@app.route('/clock-out', methods=['POST'])
def clock_out():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if user:
        log = ClockLog.query.filter_by(user_id=user.id, clock_out=None).first()
        if log:
            log.clock_out = datetime.now()
            db.session.commit()
            return jsonify({"status": "success", "message": "Clock-out successful"}), 200
        return jsonify({"status": "fail", "message": "No active clock-in found"}), 400
    return jsonify({"status": "fail", "message": "User not found"}), 404

@app.route('/hours-worked', methods=['GET'])
def hours_worked():
    username = request.args.get('username')
    user = User.query.filter_by(username=username).first()
    if user:
        logs = ClockLog.query.filter_by(user_id=user.id).all()
        total_hours = sum(
            (log.clock_out - log.clock_in).total_seconds() / 3600
            for log in logs if log.clock_out
        )
        hourly_rate = 20  # Example hourly rate
        total_payment = total_hours * hourly_rate
        return jsonify({"total_hours": total_hours, "total_payment": total_payment}), 200
    return jsonify({"status": "fail", "message": "User not found"}), 404

if __name__ == '__main__':
    app.run(debug=True)
