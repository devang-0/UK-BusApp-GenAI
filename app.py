import csv

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
# import csv
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///busApp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'notsecret'
db = SQLAlchemy(app)
# bookings = []

'''
 user and booking models for the database
'''

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(10), unique=True, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    bookings = db.relationship('Booking', backref='user', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bus = db.Column(db.String(10), nullable=False)
    source = db.Column(db.String(50), nullable=False)
    destination = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(8), nullable=False)

with app.app_context():
    db.create_all()

# def load_schedules():
#     schedules = []
#     csv_path = os.path.join(os.path.dirname(__file__), 'schedules_full.csv')
#     with open(csv_path, newline='', encoding='utf-8') as csvfile:
#         reader = csv.DictReader(csvfile)
#         for row in reader:
#             schedules.append(row)
#     return schedules

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        phone = request.form['phone']
        email = request.form['email']
        password = request.form['password']
        if not phone and not email:
            flash('Please enter a valid phone number or email address.')
            return redirect(url_for('register'))
        existing_user = User.query.filter(
            (User.email == email) | (User.phone == phone)
        ).first()
        if existing_user:
            flash('A user with that phone number or email address has already registered.')
            return redirect(url_for('register'))
        password_hash = generate_password_hash(password)
        user = User(phone=phone, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_input = request.form['login']
        password = request.form['password']
        user = User.query.filter(
            (User.email == login_input) | (User.phone == login_input)
        ).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_email'] = user.email
            flash('Login successful.')
            return redirect(url_for('home'))
        else:
            flash('Invalid login credentials. Please try again.')
        return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logout successful.')
    return redirect(url_for('login'))

def load_schedules():
    schedules = []
    csv_path = os.path.join(os.path.dirname(__file__), 'schedules_full.csv')
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            schedules.append(row)
    return schedules

@app.route('/')
def home():
    schedules = load_schedules()
    stations = sorted(set([s['source'] for s in schedules] + [s['destination'] for s in schedules]))
    return render_template('home.html', stations=stations)

@app.route('/schedule')
def schedule():
    schedules = load_schedules()
    source = request.args.get('source')
    destination = request.args.get('destination')
    date = request.args.get('date')
    filtered = [
        s for s in schedules
        if (not source or s['source'] == source) and
           (not destination or s['destination'] == destination) and
           (not date or s['date'] == date)
    ]
    return render_template('schedule.html',
                           schedules=filtered,
                           source=source,
                           destination=destination,
                           date=date)

# @app.route('/book', methods=['GET', 'POST'])
# def book():
#     if request.method == 'GET':
#         bus = request.args.get('bus')
#         source = request.args.get('source')
#         destination = request.args.get('destination')
#         date = request.args.get('date')
#         time = request.args.get('time')
#         # If no params, show info message
#         if not (bus and source and destination and date and time):
#             return render_template('book_direct.html')
#         return render_template('book.html', bus=bus, source=source, destination=destination, date=date, time=time)
#     else:
#         name = request.form['name']
#         email = request.form['email']
#         bus = request.form['bus']
#         source = request.form['source']
#         destination = request.form['destination']
#         date = request.form['date']
#         time = request.form['time']
#         booking = {
#             'name': name,
#             'email': email,
#             'bus': bus,
#             'source': source,
#             'destination': destination,
#             'date': date,
#             'time': time
#         }
#         bookings.append(booking)
#         return redirect(url_for('confirmation', name=name, bus=bus, source=source, destination=destination, date=date, time=time))
#
# @app.route('/confirmation')
# def confirmation():
#     name = request.args.get('name')
#     bus = request.args.get('bus')
#     source = request.args.get('source')
#     destination = request.args.get('destination')
#     date = request.args.get('date')
#     time = request.args.get('time')
#     return render_template('confirmation.html', name=name, bus=bus, source=source, destination=destination, date=date, time=time)
@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'POST':
        bus = request.form['bus']
        source = request.form['source']
        destination = request.form['destination']
        date = request.form['date']
        time = request.form['time']
        user_id = session['user_id']
        booking = Booking(user_id=user_id, bus=bus, source=source, destination=destination, date=date, time=time)
        db.session.add(booking)
        db.session.commit()
        flash('Booking successful!.')
        return redirect(url_for('my_bookings'))
    else:
        bus = request.args.get('bus')
        source = request.args.get('source')
        destination = request.args.get('destination')
        date = request.args.get('date')
        time = request.args.get('time')
        return render_template('book.html', bus=bus, source=source, destination=destination, date=date, time=time)

@app.route('/my_bookings')
@login_required
def my_bookings():
    user_id = session['user_id']
    user = User.query.get(user_id)
    bookings = user.bookings
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/confirmation')
@login_required
def confirmation():
    return render_template('confirmation.html')
if __name__ == '__main__':
    app.run(debug=True)
