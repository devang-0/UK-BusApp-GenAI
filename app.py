from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import csv
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai

app = Flask(__name__)
app.config['SECRET_KEY'] = 'notsecrettt'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    bookings = db.relationship('Booking', backref='booker', lazy=True)  # Link to bookings

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Link to User
    bus = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_email = db.Column(db.String(120), nullable=False)
    num_passengers = db.Column(db.Integer, nullable=False, default=1)

    def __repr__(self):
        return f"Booking('{self.bus}', '{self.source}' to '{self.destination}', on '{self.date}')"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


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


@app.route('/chatbot_api', methods=['POST'])
@login_required
def chatbot_api():

    user_message = request.json.get('message')

    if not user_message:
        return jsonify({"response": "No message provided."}), 400

    try:
        chat_session = model.start_chat(history=[])
        response = chat_session.send_message(user_message)
        return jsonify({"response": response.text})
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return jsonify({"response": "Sorry, I'm having trouble connecting to the AI. Please try again later."}), 500

@app.route('/chatbot')
@login_required
def chatbot_page():
    return render_template('chatbot.html')

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


@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'GET':
        bus = request.args.get('bus')
        source = request.args.get('source')
        destination = request.args.get('destination')
        date = request.args.get('date')
        time = request.args.get('time')

        if not (bus and source and destination and date and time):
            flash('Please select a bus from the schedule to book your seat.', 'info')
            return render_template('book_direct.html')


        passenger_name = current_user.username if current_user.is_authenticated else ''
        passenger_email = current_user.email if current_user.is_authenticated else ''

        return render_template('book.html',
                               bus=bus,
                               source=source,
                               destination=destination,
                               date=date,
                               time=time,
                               passenger_name=passenger_name,
                               passenger_email=passenger_email,
                               num_passengers = 1)
    else:
        name = request.form['name']
        email = request.form['email']
        bus = request.form['bus']
        source = request.form['source']
        destination = request.form['destination']
        date = request.form['date']
        time = request.form['time']
        num_passengers = request.form.get('num_passengers', 1, type=int)

        new_booking = Booking(
            user_id=current_user.id,
            bus=bus,
            source=source,
            destination=destination,
            date=date,
            time=time,
            passenger_name=name,
            passenger_email=email,
            num_passengers=num_passengers
        )
        db.session.add(new_booking)
        db.session.commit()

        flash(f'Thank you, {name}! Your seat on {bus} from {source} to {destination} on {date} at {time} is confirmed for {num_passengers} passenger(s).', 'success')
        return redirect(url_for('my_bookings'))  #


@app.route('/confirmation')
def confirmation():
    name = request.args.get('name')
    bus = request.args.get('bus')
    source = request.args.get('source')
    destination = request.args.get('destination')
    date = request.args.get('date')
    time = request.args.get('time')
    return render_template('confirmation.html', name=name, bus=bus, source=source, destination=destination, date=date,
                           time=time)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))

        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already registered. Please login or use a different email.', 'danger')
            return redirect(url_for('register'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/my_bookings')
@login_required
def my_bookings():

    bookings = current_user.bookings
    return render_template('my_bookings.html', bookings=bookings)


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)