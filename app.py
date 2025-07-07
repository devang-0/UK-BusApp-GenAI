from flask import Flask, render_template, request, redirect, url_for
import csv
import os

app = Flask(__name__)

bookings = []

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

# Handle direct /book route gracefully
@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'GET':
        bus = request.args.get('bus')
        source = request.args.get('source')
        destination = request.args.get('destination')
        date = request.args.get('date')
        time = request.args.get('time')
        # If no params, show info message
        if not (bus and source and destination and date and time):
            return render_template('book_direct.html')
        return render_template('book.html', bus=bus, source=source, destination=destination, date=date, time=time)
    else:
        name = request.form['name']
        email = request.form['email']
        bus = request.form['bus']
        source = request.form['source']
        destination = request.form['destination']
        date = request.form['date']
        time = request.form['time']
        booking = {
            'name': name,
            'email': email,
            'bus': bus,
            'source': source,
            'destination': destination,
            'date': date,
            'time': time
        }
        bookings.append(booking)
        return redirect(url_for('confirmation', name=name, bus=bus, source=source, destination=destination, date=date, time=time))

@app.route('/confirmation')
def confirmation():
    name = request.args.get('name')
    bus = request.args.get('bus')
    source = request.args.get('source')
    destination = request.args.get('destination')
    date = request.args.get('date')
    time = request.args.get('time')
    return render_template('confirmation.html', name=name, bus=bus, source=source, destination=destination, date=date, time=time)

if __name__ == '__main__':
    app.run(debug=True)
