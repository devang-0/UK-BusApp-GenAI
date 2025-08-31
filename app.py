# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# IMPORTS & BASIC SETUP
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import csv
import os
import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
import json
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# APP CONFIG
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
app = Flask(__name__)
load_dotenv()
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')
user_chat_history = {}
csrf = CSRFProtect(app)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# loads schedule data from CSV on startup
def load_schedules_from_csv():
    schedules = []
    csv_path = os.path.join(os.path.dirname(__file__), 'schedules_full.csv')
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            schedules.append(row)
    return schedules

ALL_SCHEDULES = load_schedules_from_csv()


# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# DATABASE MODELS
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    bookings = db.relationship('Booking', backref='booker', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    bus_route_id = db.Column(db.String(50), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    operating_days = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_email = db.Column(db.String(120), nullable=False)
    num_passengers = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False, default=0.0)
    duration = db.Column(db.String(20), nullable=False)
    total_cost = db.Column(db.Float, nullable=False, default=0.0)
    name_on_card = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Confirmed')

    def __repr__(self):
        return f"Booking('{self.bus_route_id}', '{self.source}' to '{self.destination}', on '{self.operating_days}' at '{self.time}', Passengers: {self.num_passengers}, Cost: £{self.total_cost:.2f}')"


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# FLASK ROUTES
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
@app.route('/')
def home():
    stations = sorted(set([s['source'] for s in ALL_SCHEDULES] + [s['destination'] for s in ALL_SCHEDULES]))
    return render_template('home.html', stations=stations)


@app.route('/schedule')
def schedule():
    source_filter = request.args.get('source')
    destination_filter = request.args.get('destination')
    date_filter = request.args.get('date')

    stations = sorted(set([s['source'] for s in ALL_SCHEDULES] + [s['destination'] for s in ALL_SCHEDULES]))

    search_date_obj = None
    if date_filter:
        try:
            search_date_obj = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
        except ValueError:
            flash(f"Invalid date provided: '{date_filter}'. Please check the format.", 'danger')
            return render_template('schedule.html',
                                   schedules=[],
                                   source=source_filter,
                                   destination=destination_filter,
                                   date=date_filter,
                                   stations=stations)

    filtered_schedules = []

    if source_filter or destination_filter or date_filter:
        for s in ALL_SCHEDULES:
            match_source = (not source_filter or s['source'] == source_filter)
            match_destination = (not destination_filter or s['destination'] == destination_filter)
            match_operating_days_criteria = True

            if date_filter:
                try:
                    search_date_obj = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
                    day_of_week = search_date_obj.weekday()
                    is_weekday = day_of_week < 5
                    is_weekend = day_of_week >= 5
                    schedule_day_type = s['operating_days'].lower()

                    if schedule_day_type == 'everyday':
                        match_operating_days_criteria = True
                    elif schedule_day_type == 'weekdays' and is_weekday:
                        match_operating_days_criteria = True
                    elif schedule_day_type == 'weekends' and is_weekend:
                        match_operating_days_criteria = True
                    else:
                        match_operating_days_criteria = False
                except ValueError:
                    pass

            if match_source and match_destination and match_operating_days_criteria:
                filtered_schedules.append(s)

    return render_template('schedule.html',
                           schedules=filtered_schedules,
                           source=source_filter,
                           destination=destination_filter,
                           date=date_filter,
                           stations=stations)


@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'GET':
        bus_route_id = request.args.get('bus_route_id')
        time = request.args.get('time')

        if not bus_route_id or not time:
            flash('Please select a bus from the schedule to book your seat.', 'info')
            return render_template('book_direct.html')

        trip_details = None
        for s in ALL_SCHEDULES:
            if s['bus_route_id'] == bus_route_id and s['time'] == time:
                trip_details = s
                break

        if not trip_details:
            print(f"SECURITY WARNING: Failed attempt to book non-existent trip. ID: {bus_route_id}, Time: {time}")
            flash('The selected bus route is invalid. Please do not alter the URL.', 'danger')
            return redirect(url_for('schedule'))

        passenger_name = current_user.username
        passenger_email = current_user.email
        num_passengers = 1
        price = float(trip_details.get('price', 0.0))
        calculated_cost = num_passengers * price

        return render_template('book.html',
                               bus_route_id=trip_details['bus_route_id'],
                               source=trip_details['source'],
                               destination=trip_details['destination'],
                               operating_days=trip_details['operating_days'],
                               time=trip_details['time'],
                               price=price,
                               duration=trip_details['duration'],
                               passenger_name=passenger_name,
                               passenger_email=passenger_email,
                               num_passengers=num_passengers,
                               total_cost=calculated_cost)

    else:
        name = request.form['name']
        email = request.form['email']
        bus_route_id = request.form['bus_route_id']
        source = request.form['source']
        destination = request.form['destination']
        operating_days = request.form['operating_days']
        time = request.form['time']
        price = request.form['price']
        duration = request.form['duration']
        num_passengers = request.form.get('num_passengers', 1, type=int)

        final_total_cost = num_passengers * float(price)

        session['booking_details'] = {
            'name': name, 'email': email, 'bus_route_id': bus_route_id,
            'source': source, 'destination': destination, 'operating_days': operating_days,
            'time': time, 'price': price, 'duration': duration,
            'num_passengers': num_passengers, 'total_cost': final_total_cost
        }
        return redirect(url_for('process_payment'))


@app.route('/process_payment', methods=['GET', 'POST'])
@login_required
def process_payment():
    booking_details = session.get('booking_details')
    if not booking_details:
        flash('No booking details found. Please select a bus again.', 'danger')
        return redirect(url_for('home'))

    if request.method == 'POST':
        name_on_card = request.form.get('name_on_card')
        card_number = request.form.get('card_number')
        expiry_month = request.form.get('expiry_month')
        expiry_year = request.form.get('expiry_year')
        cvv = request.form.get('cvv')

        errors = []
        if not name_on_card or len(name_on_card.strip()) == 0:
            errors.append("Name on Card is required.")

        cleaned_card_number = card_number.replace(" ", "")
        if not cleaned_card_number.isdigit() or not (13 <= len(cleaned_card_number) <= 19):
            errors.append("Invalid Card Number (must be 13-19 digits).")

        current_year = datetime.datetime.now().year
        current_month = datetime.datetime.now().month
        try:
            exp_month = int(expiry_month)
            exp_year = int(expiry_year)
            if not (1 <= exp_month <= 12):
                errors.append("Invalid Expiry Month.")
            if exp_year < current_year or (exp_year == current_year and exp_month < current_month):
                errors.append("Card has expired.")
        except ValueError:
            errors.append("Invalid Expiry Date format.")

        if not cvv or not cvv.isdigit() or not (3 <= len(cvv) <= 4):
            errors.append("Invalid CVV (must be 3 or 4 digits).")

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('process_payment.html', booking_details=booking_details, now=datetime.datetime.now())

        new_booking = Booking(
            user_id=current_user.id,
            bus_route_id=booking_details['bus_route_id'],
            source=booking_details['source'],
            destination=booking_details['destination'],
            operating_days=booking_details['operating_days'],
            time=booking_details['time'],
            passenger_name=booking_details['name'],
            passenger_email=booking_details['email'],
            num_passengers=booking_details['num_passengers'],
            price=float(booking_details['price']),
            duration=booking_details['duration'],
            total_cost=booking_details['total_cost'],
            name_on_card=name_on_card,
            status='Confirmed'
        )
        db.session.add(new_booking)
        db.session.commit()

        session.pop('booking_details', None)

        flash(
            f'Payment successful! Your booking for {booking_details["bus_route_id"]} (Total: £{booking_details["total_cost"]:.2f}) is confirmed.','success')
        return redirect(url_for('my_bookings'))

    return render_template('process_payment.html', booking_details=booking_details, now=datetime.datetime.now())


# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# USER AUTHENTICATION ROUTES
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
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


# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# BOOKING MANAGEMENT ROUTES
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
@app.route('/my_bookings')
@login_required
def my_bookings():
    user_id = current_user.id
    bookings = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).all()
    return render_template('my_bookings.html', bookings=bookings)


@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        flash('You are not authorized to cancel this booking.', 'danger')
        return redirect(url_for('my_bookings'))

    booking.status = 'Cancelled'
    db.session.commit()

    flash(f'Your booking for {booking.bus_route_id} from {booking.source} to {booking.destination} has been cancelled. Please note that no refunds will be provided.', 'success')
    return redirect(url_for('my_bookings'))


# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# CHATBOT ROUTES
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
@app.route('/chatbot_api', methods=['POST'])
@login_required
def chatbot_api():
    user_message = request.json.get('message')
    user_id = current_user.id

    if not user_message:
        return jsonify({"response": "<p>No message provided.</p>"}), 400

    if user_id not in user_chat_history:
        user_chat_history[user_id] = [
            {'role': 'user', 'parts': ['As an AI bus assistant, all your responses must use basic HTML for formatting. Use <p>, <strong>, and <ul>/<li> tags. Be polite and helpful.']},
            {'role': 'model', 'parts': ['<p>Understood. I will provide all my responses using basic HTML formatting.</p>']}]

    try:
        #1.detect user intent
        temp_chat_session_for_intent = model.start_chat(history=[])
        intent_prompt = f"""
        Classify the user's query into one of these categories: "schedule_query", "app_help", "cost_query", "general_conversation".
        Return ONLY the category name. Query: "{user_message}"
        """
        intent_response = temp_chat_session_for_intent.send_message(intent_prompt)
        detected_intent = intent_response.text.strip().lower()
        print(f"Detected Intent: '{detected_intent}'")

        final_ai_response = ""
        actual_chat_session = model.start_chat(history=user_chat_history[user_id])

        #2.handles response based on the intent
        if detected_intent == "app_help":
            if "cancel" in user_message.lower():
                final_ai_response = "<p>To cancel a booking, please go to the <strong>'My Bookings'</strong> page from the navigation bar. You will see a 'Cancel' button next to each of your confirmed bookings.</p>"
            elif "register" in user_message.lower():
                final_ai_response = "<p>To create an account, click on the <strong>'Register'</strong> link in the navigation bar at the top of the page and fill out the form.</p>"
            else:
                final_ai_response = """
                <p>Hello! I can help you with how to use UK BusApp.</p>
                <strong>To book a ticket:</strong>
                <ul>
                    <li>Search for your desired route and date on the homepage.</li>
                    <li>Once you find a suitable bus, click the 'Book' button.</li>
                    <li>You will be redirected to the booking form to confirm details and complete the simulated payment.</li>
                </ul>
                """

        elif detected_intent == "cost_query":
            #extract cities and find prices
            extraction_prompt = f"""
            Extract 'source city' and 'destination city' from the user query. Return as a JSON object.
            Query: "{user_message}" -> {{"source": "...", "destination": "..."}}
            """
            extraction_response = actual_chat_session.send_message(extraction_prompt)
            try:
                json_start = extraction_response.text.find('{')
                json_end = extraction_response.text.rfind('}')
                extracted_params = json.loads(extraction_response.text[json_start:json_end + 1])
                source = extracted_params.get('source')
                destination = extracted_params.get('destination')

                specific_schedule = next((s for s in ALL_SCHEDULES if source and destination and s['source'].lower() == source.lower() and s[ 'destination'].lower() == destination.lower()), None)

                if specific_schedule:
                    price = specific_schedule['price']
                    final_ai_response = f"<p>A ticket from <strong>{source.title()}</strong> to <strong>{destination.title()}</strong> costs approximately <strong>£{price}</strong>. The final price may vary based on the specific time and service.</p>"
                else:
                    final_ai_response = "<p>Ticket prices vary by route. For an accurate price, please search for your specific journey on the home page.</p>"
            except (json.JSONDecodeError, ValueError):
                final_ai_response = "<p>Each bus ticket has a dynamic price. The total cost will be calculated and displayed on the booking page.</p>"

        elif detected_intent == "schedule_query":
            #extract cities and searches for schedules
            extraction_prompt = f"""
            From the user query below, extract the 'source' city and 'destination' city.
            Return ONLY a valid JSON object in the format {{"source": "...", "destination": "..."}}.
            If a value is not found, use null. Do not add any other text, explanation, or markdown formatting.

            Query: "{user_message}"
            """
            extraction_response = actual_chat_session.send_message(extraction_prompt)
            try:
                json_start = extraction_response.text.find('{')
                json_end = extraction_response.text.rfind('}')
                if json_start == -1 or json_end == -1:
                    raise json.JSONDecodeError("No JSON object found", extraction_response.text, 0)

                extracted_params = json.loads(extraction_response.text[json_start:json_end + 1])
                source_query = extracted_params.get('source')
                destination_query = extracted_params.get('destination')

                if not source_query and not destination_query:
                    final_ai_response = "<p>I can help you find a bus! Please tell me where you'd like to travel from and to (for example: 'bus from London to Manchester').</p>"
                else:
                    found_schedules = []
                    for s in ALL_SCHEDULES:
                        match_source = (not source_query or (s['source'] and source_query.lower() in s['source'].lower()))
                        match_destination = (not destination_query or (s['destination'] and destination_query.lower() in s['destination'].lower()))
                        if match_source and match_destination:
                            found_schedules.append(s)

                    if found_schedules:
                        schedules_list_html = "<ul>" + "".join([f"<li>Route <strong>{s['bus_route_id']}</strong> from <strong>{s['source']}</strong> to <strong>{s['destination']}</strong> at {s['time']}</li>"
                         for s in found_schedules[:5]]) + "</ul>"
                        final_ai_response = f"<p>Certainly! Here are some schedules I found for you:</p>{schedules_list_html}"
                    else:
                        final_ai_response = f"<p>I'm sorry, I couldn't find any schedules from <strong>{(source_query or 'anywhere').title()}</strong> to <strong>{(destination_query or 'anywhere').title()}</strong>. Please check your spelling or try another route.</p>"

            except (json.JSONDecodeError, ValueError):
                final_ai_response = "<p>I couldn't quite understand the route. Could you please state the departure and arrival cities clearly? For example: 'bus from London to Manchester'.</p>"

        else: #if general conversation
            if "speed" in user_message.lower() or "test" in user_message.lower():
                final_ai_response = "<p>I am a bus booking assistant and cannot perform that kind of test. How can I help you with your travel plans?</p>"
            else:
                response = actual_chat_session.send_message(
                    f"The user said: '{user_message}'. Provide a brief, friendly, and conversational response, remembering to use HTML tags.")
                final_ai_response = response.text

        #3. updates and save chat history
        user_chat_history[user_id].append({'role': 'user', 'parts': [user_message]})
        user_chat_history[user_id].append({'role': 'model', 'parts': [final_ai_response]})
        return jsonify({"response": final_ai_response})

    except Exception as e:
        print(f"Global Error calling Gemini API: {e}")
        return jsonify({"response": "<p>Sorry, I'm having trouble connecting. Please try again later.</p>"}), 500


@app.route("/chatbot")
@login_required
def chatbot_page():
    return render_template('chatbot.html')


# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*
# RUN APP
# -*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*-*

if __name__ == '__main__':
    app.run(debug=False)