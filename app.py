from flask import Flask, render_template, request

app = Flask(__name__)

# Sample static bus schedule data
bus_schedule = [
    {"source": "Birmingham", "destination": "Manchester", "departure": "10:00", "arrival": "13:00"},
    {"source": "London", "destination": "Leeds", "departure": "12:00", "arrival": "16:00"},
    {"source": "Birmingham", "destination": "Leeds", "departure": "08:00", "arrival": "11:30"},
    {"source": "Manchester", "destination": "London", "departure": "09:00", "arrival": "13:00"}
]


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    filtered_buses = bus_schedule

    if request.method == 'POST':
        source = request.form.get('source')
        destination = request.form.get('destination')
        filtered_buses = [bus for bus in bus_schedule if
                          bus['source'].lower() == source.lower() and bus['destination'].lower() == destination.lower()]

    return render_template('schedule.html', buses=filtered_buses)


if __name__ == '__main__':
    app.run(debug=True)
