import pytest
from app import app, db, User, Booking, ALL_SCHEDULES

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    client = app.test_client()

    with app.app_context():
        db.create_all()

    yield client

    with app.app_context():
        db.drop_all()



def test_password_hashing():
    u = User(username='testuser', email='test@example.com')
    u.set_password('mysecretpassword')
    assert u.check_password('mysecretpassword') is True
    assert u.check_password('wrongpassword') is False


# CHANGE #2: The test now checks the ALL_SCHEDULES variable directly
def test_load_schedules():
    """
    Tests if the ALL_SCHEDULES global variable is loaded correctly.
    """
    schedules = ALL_SCHEDULES
    assert isinstance(schedules, list)
    assert len(schedules) > 0
    assert 'bus_route_id' in schedules[0]



def test_registration_and_login(client):
    response = client.post('/register', data=dict(
        username='testlogin', email='testlogin@example.com', password='password123'
    ), follow_redirects=True)
    assert b"Your account has been created!" in response.data

    response = client.post('/login', data=dict(
        email='testlogin@example.com', password='password123'
    ), follow_redirects=True)
    assert b"Login successful!" in response.data
    assert b"Logout (testlogin)" in response.data

    response = client.get('/logout', follow_redirects=True)
    assert b"You have been logged out." in response.data


def test_duplicate_registration(client):
    client.post('/register', data={'username': 'duplicate', 'email': 'duplicate@test.com', 'password': 'pw'})
    response = client.post('/register',
                           data={'username': 'anotheruser', 'email': 'duplicate@test.com', 'password': 'pw'},
                           follow_redirects=True)
    assert b"Email already registered." in response.data


def test_protected_route_access(client):
    response = client.get('/my_bookings', follow_redirects=True)
    assert b"Sign In to Your Account" in response.data


def test_full_booking_journey(client):
    client.post('/register', data={'username': 'booker', 'email': 'booker@test.com', 'password': 'pw'})
    client.post('/login', data={'email': 'booker@test.com', 'password': 'pw'}, follow_redirects=True)

    client.post('/book', data=dict(
        bus_route_id='LBH01', source='London', destination='Birmingham', operating_days='Everyday',
        time='08:00', price='15.00', duration='3h 30m', name='booker',
        email='booker@test.com', num_passengers=1
    ), follow_redirects=True)
    client.post('/process_payment', data=dict(
        name_on_card='Test Booker', card_number='1111222233334444',
        expiry_month='12', expiry_year='2028', cvv='123'
    ), follow_redirects=True)

    response = client.get('/my_bookings')
    assert b"LBH01" in response.data
    assert b"Confirmed" in response.data

    with app.app_context():
        booking_to_cancel = Booking.query.filter_by(passenger_name='booker').first()
        assert booking_to_cancel is not None
        booking_id = booking_to_cancel.id

    response = client.post(f'/cancel_booking/{booking_id}', follow_redirects=True)
    assert b"has been cancelled" in response.data

    response = client.get('/my_bookings')
    assert b"Cancelled" in response.data
    assert b"Confirmed" not in response.data


def test_chatbot_api(client):
    client.post('/register', data={'username': 'chatter', 'email': 'chatter@test.com', 'password': 'pw'})
    client.post('/login', data={'email': 'chatter@test.com', 'password': 'pw'}, follow_redirects=True)
    response = client.post('/chatbot_api', json={'message': 'hi'})
    assert response.status_code == 200
    assert 'response' in response.get_json()