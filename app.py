from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import csv
import os
import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'notsecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

user_chat_history = {}

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

    def __repr__(self):
        return f"Booking('{self.bus_route_id}', '{self.source}' to '{self.destination}', on '{self.operating_days}' at '{self.time}', Passengers: {self.num_passengers})"

with app.app_context():
    db.create_all()

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

@app.route('/schedule')
def schedule():
    schedules = load_schedules()
    source_filter = request.args.get('source')
    destination_filter = request.args.get('destination')
    date_filter = request.args.get('date')
    operating_days_filter = request.args.get('operating_days')

    stations = sorted(set([s['source'] for s in schedules] + [s['destination'] for s in schedules]))
    operating_days_options = sorted(list(set([s['operating_days'] for s in schedules])))
    filtered_schedules = []
    for s in schedules:
        match_source = (not source_filter or s['source'] == source_filter)
        match_destination = (not destination_filter or s['destination'] == destination_filter)

        match_operating_days_criteria = True
        if date_filter:
            try:
                search_date = datetime.datetime.strptime(date_filter, '%Y-%m-%d').date()
                day_of_week = search_date.weekday()

                is_weekday = day_of_week < 5
                is_weekend = day_of_week >= 5

                schedule_day_type = s['operating_days'].lower()

                if schedule_day_type == 'daily':
                    match_operating_days_criteria = True
                elif schedule_day_type == 'weekdays' and is_weekday:
                    match_operating_days_criteria = True
                elif schedule_day_type == 'weekends' and is_weekend:
                    match_operating_days_criteria = True
                else:
                    match_operating_days_criteria = False
            except ValueError:
                pass

        if operating_days_filter:
            if operating_days_filter.lower() == s['operating_days'].lower():
                match_operating_days_criteria = True
            else:
                match_operating_days_criteria = False

        if match_source and match_destination and match_operating_days_criteria:
            filtered_schedules.append(s)

    return render_template('schedule.html',
                           schedules=filtered_schedules,
                           source=source_filter,
                           destination=destination_filter,
                           date=date_filter,
                           operating_days=operating_days_filter,
                           stations=stations,
                           operating_days_options=operating_days_options)

@app.route('/book', methods=['GET', 'POST'])
@login_required
def book():
    if request.method == 'GET':
        bus_route_id = request.args.get('bus_route_id')
        source = request.args.get('source')
        destination = request.args.get('destination')
        operating_days = request.args.get('operating_days')
        time = request.args.get('time')

        passenger_name = current_user.username if current_user.is_authenticated else ''
        passenger_email = current_user.email if current_user.is_authenticated else ''

        if not (bus_route_id and source and destination and operating_days and time):
            flash('Please select a bus from the schedule to book your seat.', 'info')
            return render_template('book_direct.html')

        return render_template('book.html',
                               bus_route_id=bus_route_id,
                               source=source,
                               destination=destination,
                               operating_days=operating_days,
                               time=time,
                               passenger_name=passenger_name,
                               passenger_email=passenger_email,
                               num_passengers=1)
    else:
        name = request.form['name']
        email = request.form['email']
        bus_route_id = request.form['bus_route_id']
        source = request.form['source']
        destination = request.form['destination']
        operating_days = request.form['operating_days']
        time = request.form['time']
        num_passengers = request.form.get('num_passengers', 1, type=int)

        new_booking = Booking(
            user_id=current_user.id,
            bus_route_id=bus_route_id,
            source=source,
            destination=destination,
            operating_days=operating_days,
            time=time,
            passenger_name=name,
            passenger_email=email,
            num_passengers=num_passengers
        )
        db.session.add(new_booking)
        db.session.commit()

        flash(
            f'Thank you, {name}! Your seat(s) on {bus_route_id} from {source} to {destination} ({operating_days} at {time}) are confirmed for {num_passengers} passenger(s).',
            'success')
        return redirect(url_for('my_bookings'))

@app.route('/confirmation')
def confirmation():
    name = request.args.get('name')
    bus_route_id = request.args.get('bus_route_id')
    source = request.args.get('source')
    destination = request.args.get('destination')
    operating_days = request.args.get('operating_days')
    time = request.args.get('time')
    return render_template('confirmation.html', name=name, bus_route_id=bus_route_id, source=source,
                           destination=destination, operating_days=operating_days, time=time)

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
    user_id = current_user.id
    bookings = current_user.bookings
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        flash('You are not authorized to cancel this booking.', 'danger')
        return redirect(url_for('my_bookings'))

    db.session.delete(booking)
    db.session.commit()

    flash(
        f'Your booking for {booking.bus_route_id} from {booking.source} to {booking.destination} on {booking.operating_days} at {booking.time} has been cancelled.', 'success')
    return redirect(url_for('my_bookings'))


@app.route('/chatbot_api', methods=['POST'])
@login_required
def chatbot_api():
    user_message = request.json.get('message')
    user_id = current_user.id

    if not user_message:
        return jsonify({"response": "No message provided."}), 400

    if user_id not in user_chat_history:
        user_chat_history[user_id] = []

    try:
        temp_chat_session_for_intent = model.start_chat(history=[])

        intent_prompt = f"""
        Analyze the user's query and classify its primary intent into ONLY one of these exact categories:
        - schedule_query (if asking for bus schedules, routes, times, or journeys between places, e.g., "buses from London", "schedule to Leeds", "bus", "timetable")
        - app_help (if asking how to use the application, how to book, how to cancel, manage account, etc., e.g., "how to book", "how to cancel", "manage tickets", "help me")
        - general_conversation (for greetings, casual chat, questions about current date/time/weather, or anything else not directly about bus schedules or app functionality)

        Return ONLY the category name, without any other words, punctuation, or explanation.
        Query: "{user_message}"
        """

        intent_response = temp_chat_session_for_intent.send_message(intent_prompt)
        detected_intent = intent_response.text.strip().lower()
        print(f"Detected Intent: '{detected_intent}'")

        final_ai_response = ""

        actual_chat_session = model.start_chat(history=user_chat_history[user_id])

        if not user_chat_history[
            user_id] and detected_intent == "general_conversation":
            initial_system_message = {'role': 'user', 'parts': [
                'As an AI bus assistant, respond politely and helpfully. For general queries, be conversational. For schedule-related queries, help find buses based on data provided later.']}
            actual_chat_session = model.start_chat(history=[initial_system_message, {'role': 'model', 'parts': [
                'Understood. I will do my best to assist you.']}])
            user_chat_history[user_id].extend(
                [initial_system_message, {'role': 'model', 'parts': ['Understood. I will do my best to assist you.']}])

        if detected_intent == "general_conversation":
            general_response = actual_chat_session.send_message(user_message)
            final_ai_response = general_response.text
            print(f"General Response from AI: '{final_ai_response}'")

        elif detected_intent == "app_help":
            app_help_response = f"""
            To book a ticket, first search for your desired route and date on the homepage or schedule page.
            Once you find a suitable bus, click the 'Book' button next to it.
            You will be redirected to the booking form where you can confirm details and specify the number of tickets.
            You must be logged in to book a ticket.
            To manage your bookings, visit the 'My Bookings' page accessible from the navigation bar after logging in.
            There you can view your existing tickets and cancel them.
            """
            final_ai_response = app_help_response
            print(f"App Help Response (predefined): '{final_ai_response}'")

        elif detected_intent == "schedule_query":
            extraction_prompt = f"""
            Extract bus travel information from the following user query.
            Look for: 'source city', 'destination city', and 'travel day' (e.g., "Daily", "Weekdays", "Weekends", or a specific date in YYYY-MM-DD format).
            Return the information as a JSON object. If a piece of information is not found, use null.
            Example: "I want to go from London to Birmingham on 2025-07-28." -> {{"source": "London", "destination": "Birmingham", "day_type": null, "date": "2025-07-28"}}
            Example: "Buses to Manchester on weekends" -> {{"source": null, "destination": "Manchester", "day_type": "Weekends", "date": null}}
            Example: "Buses from Leeds" -> {{"source": "Leeds", "destination": null, "day_type": null, "date": null}}
            Query: "{user_message}"
            """

            extraction_response = actual_chat_session.send_message(extraction_prompt)

            try:
                json_start = extraction_response.text.find('{')
                json_end = extraction_response.text.rfind('}')
                if json_start == -1 or json_end == -1:
                    raise json.JSONDecodeError("No JSON object found in LLM response", extraction_response.text, 0)

                extracted_info_str = extraction_response.text[json_start: json_end + 1]
                extracted_params = json.loads(extracted_info_str)

                source_query = extracted_params.get('source')
                destination_query = extracted_params.get('destination')
                day_type_query = extracted_params.get('day_type')
                date_query = extracted_params.get('date')

                if not source_query and not destination_query:
                    final_ai_response = "I can help you find bus schedules! Which cities are you interested in (e.g., source and destination)?"
                else:
                    all_schedules = load_schedules()
                    found_schedules = []

                    for s in all_schedules:
                        match_source = (
                                    not source_query or (s['source'] and s['source'].lower() == source_query.lower()))
                        match_destination = (not destination_query or (
                                    s['destination'] and s['destination'].lower() == destination_query.lower()))

                        match_day_criteria = True

                        if day_type_query:
                            if day_type_query.lower() != s['operating_days'].lower():
                                match_day_criteria = False
                        elif date_query:
                            try:
                                search_date = datetime.datetime.strptime(date_query, '%Y-%m-%d').date()
                                day_of_week = search_date.weekday()

                                is_weekday = day_of_week < 5
                                is_weekend = day_of_week >= 5

                                schedule_day_type = s['operating_days'].lower()

                                if schedule_day_type == 'daily':
                                    pass
                                elif schedule_day_type == 'weekdays' and is_weekday:
                                    pass
                                elif schedule_day_type == 'weekends' and is_weekend:
                                    pass
                                else:
                                    match_day_criteria = False
                            except ValueError:
                                pass

                        if match_source and match_destination and match_day_criteria:
                            found_schedules.append(s)

                    if found_schedules:
                        schedules_text = "\n".join([
                                                       f"Route {s['bus_route_id']} from {s['source']} to {s['destination']} ({s['operating_days']}) at {s['time']}"
                                                       for s in found_schedules[:10]])
                        response_prompt = f"""
                        The user asked about bus schedules. Here are the relevant schedules found in the database based on their query:
                        ---
                        {schedules_text}
                        ---

                        Please provide a helpful and conversational summary of these schedules to the user.
                        Mention the route ID, source, destination, operating days, and times clearly.
                        If the query was for a specific date, you can start by saying "For buses on {date_query}..." if relevant.
                        """
                    else:
                        response_prompt = f"""
                        The user asked about bus schedules. No schedules were found for the criteria:
                        Source: {source_query if source_query else 'any'}
                        Destination: {destination_query if destination_query else 'any'}
                        Operating Days/Date: {day_type_query if day_type_query else (date_query if date_query else 'any')}

                        Please inform the user politely that no schedules were found for their specific query. Suggest they try different routes, or specify "Daily", "Weekdays", "Weekends" for operating days, or provide dates in YYYY-MM-DD format for precise search.
                        """

                    final_response = actual_chat_session.send_message(response_prompt)
                    final_ai_response = final_response.text
                    print(f"Schedule Response from AI: '{final_ai_response}'")

            except json.JSONDecodeError:
                final_ai_response = "I couldn't fully understand your request for schedules. Could you try asking in a more direct way? For example: 'Show me buses from London to Birmingham Daily' or 'What buses from Leeds to Manchester on 2025-07-28?'"
                print(f"JSONDecode Error Response: '{final_ai_response}'")
            except Exception as e:
                print(f"Error during AI processing or data retrieval: {e}")
                final_ai_response = "Sorry, I'm having trouble processing your schedule request right now. Please try again later."
                print(f"General Error Response (Schedule): '{final_ai_response}'")

        else:
            final_ai_response = "I'm not sure what you're asking. I can help you with bus schedules. For example, 'Show me buses from London to Birmingham'."
            print(f"Fallback Intent Response: '{final_ai_response}'")

        user_chat_history[user_id].append({'role': 'user', 'parts': [user_message]})
        user_chat_history[user_id].append({'role': 'model', 'parts': [final_ai_response]})
        print(f"Updated History Length: {len(user_chat_history[user_id])}")
        print(f"--- End Chatbot Request ---")

        return jsonify({"response": final_ai_response})

    except Exception as e:
        print(f"Global Error calling Gemini API: {e}")
        return jsonify({"response": "Sorry, I'm having trouble connecting to the AI. Please try again later."}), 500

@app.route('/chatbot')
@login_required
def chatbot_page():
    return render_template('chatbot.html')


with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)