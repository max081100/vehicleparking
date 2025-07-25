# app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, ParkingLot, ParkingSpot, Reservation
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'parkinglot_secret'

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'parking.db')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Ensure DB & Admin Creation
ADMIN_EMAIL = "admin@parking.com"
ADMIN_PASSWORD = "admin"    # or "admin123" if you wish

def create_tables_and_admin():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email=ADMIN_EMAIL).first():
            hashed_pw = generate_password_hash(ADMIN_PASSWORD, method='pbkdf2:sha256')
            admin = User(name='Admin', email=ADMIN_EMAIL, password=hashed_pw, is_admin=True)
            db.session.add(admin)
            db.session.commit()
            print("Admin user created with email:", ADMIN_EMAIL, "and password:", ADMIN_PASSWORD)
create_tables_and_admin()




@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(email=email).first():
            flash('Email already exists!')
            return redirect(url_for('register'))
        user = User(name=name, email=email, password=password, is_admin=False)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful. Please login.')
        return redirect(url_for('user_login'))
    return render_template('register.html')

@app.route('/user_login', methods=['GET','POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['email']
        pw = request.form['password']
        user = User.query.filter_by(email=email, is_admin=False).first()
        if user and check_password_hash(user.password, pw):
            session['user_id'] = user.id
            session['is_admin'] = False
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('user_login.html')

@app.route('/reset_admin')
def reset_admin():
    from werkzeug.security import generate_password_hash
    from models import User, db
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        db.session.add(admin)
    admin.password = generate_password_hash('admin123')
    db.session.commit()
    return "Admin password reset to admin123"

@app.route('/admin_login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        pw = request.form['password']
        user = User.query.filter_by(email=email, is_admin=True).first()
        if user and check_password_hash(user.password, pw):
            session['admin_id'] = user.id
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials')
    return render_template('admin_login.html')

@app.route('/add_sample_lots')
def add_sample_lots():
    # Only add if table is empty
    if ParkingLot.query.count() == 0:
        lot1 = ParkingLot(name='Main Lot', location='Front Gate')
        lot2 = ParkingLot(name='West Basement', location='B2 Level')
        db.session.add_all([lot1, lot2])
        db.session.commit()

        # Add a couple of parking spots for each lot
        spot1 = ParkingSpot(lot_id=lot1.id, spot_number='A1', status='EMPTY')
        spot2 = ParkingSpot(lot_id=lot1.id, spot_number='A2', status='EMPTY')
        spot3 = ParkingSpot(lot_id=lot2.id, spot_number='B1', status='EMPTY')
        db.session.add_all([spot1, spot2, spot3])
        db.session.commit()
        return "<b>Sample lots and spots added!</b> You can now test the reservation page.<br><a href='/reserve_parking_spot'>Go to Reserve Spot</a>"
    return "Lots already exist!"



@app.route('/logout')
def logout():
    session.clear()
    flash('You have logged out.')
    return redirect(url_for('home'))

##### ADMIN ROUTES #####

@app.route('/admin_dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    users = User.query.filter_by(is_admin=False).all()
    lots = ParkingLot.query.all()
    reservations = Reservation.query.all()
    return render_template('admin_dashboard.html', users=users, lots=lots, reservations=reservations)

@app.route('/create_parking_lot', methods=['GET','POST'])
def create_parking_lot():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        num_spots = int(request.form['num_spots'])
        lot = ParkingLot(name=name, location=location)
        db.session.add(lot)
        db.session.commit()
        # Create parking spots automatically!
        for i in range(1, num_spots+1):
            spot = ParkingSpot(spot_number=f"S{i}", lot_id=lot.id)
            db.session.add(spot)
        db.session.commit()
        flash('Parking lot created.')
        return redirect(url_for('admin_dashboard'))
    return render_template('create_parking_lot.html')

@app.route('/edit_parking_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_parking_lot(lot_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    lot = ParkingLot.query.get_or_404(lot_id)
    if request.method == 'POST':
        lot.name = request.form['name']
        lot.location = request.form['location']
        db.session.commit()
        flash('Parking lot updated!')
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_parking_lot.html', lot=lot)

@app.route('/delete_parking_lot/<int:lot_id>', methods=['POST'])
def delete_parking_lot(lot_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
    for spot in spots:
        if spot.status != 'EMPTY':
            flash('Can only delete lot if all spots are EMPTY.')
            return redirect(url_for('admin_dashboard'))
    for spot in spots:
        db.session.delete(spot)
    db.session.delete(lot)
    db.session.commit()
    flash('Parking lot deleted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/parking_spots/<int:lot_id>')
def view_parking_spots(lot_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    lot = ParkingLot.query.get_or_404(lot_id)
    spots = ParkingSpot.query.filter_by(lot_id=lot.id).all()
    return render_template('view_parking_spots.html', lot=lot, spots=spots)

@app.route('/delete_parking_spot/<int:spot_id>', methods=['POST'])
def delete_parking_spot(spot_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))
    spot = ParkingSpot.query.get_or_404(spot_id)
    if spot.status != 'EMPTY':
        flash('Can only delete spot if EMPTY.')
        return redirect(url_for('view_parking_spots', lot_id=spot.lot_id))
    db.session.delete(spot)
    db.session.commit()
    flash('Spot deleted.')
    return redirect(url_for('view_parking_spots', lot_id=spot.lot_id))

##### USER ROUTES #####

@app.route('/user_dashboard')
def user_dashboard():
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    user = User.query.get(session['user_id'])
    active_reservation = Reservation.query.filter_by(user_id=user.id, end_time=None).first()
    reservations = Reservation.query.filter_by(user_id=user.id).all()
    return render_template('user_dashboard.html', user=user, active_reservation=active_reservation, reservations=reservations)

@app.route('/reserve_parking_spot', methods=['GET', 'POST'])
def reserve_parking_spot():
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    lots = ParkingLot.query.all()
    if request.method == 'POST':
        lot_id = int(request.form['lot_id'])
        spot = ParkingSpot.query.filter_by(lot_id=lot_id, status='EMPTY').first()
        if not spot:
            flash('No available spots in this lot!')
            return redirect(url_for('reserve_parking_spot'))
        spot.status = 'OCCUPIED'
        reservation = Reservation(
            user_id=session['user_id'],
            spot_id=spot.id,
            start_time=datetime.now()
        )
        db.session.add(reservation)
        db.session.commit()
        flash(f'Spot {spot.spot_number} reserved. Park your vehicle!')
        return redirect(url_for('user_dashboard'))
    return render_template('reserve_parking_spot.html', lots=lots)

@app.route('/release_parking_spot/<int:reservation_id>', methods=['POST'])
def release_parking_spot(reservation_id):
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    reservation = Reservation.query.get_or_404(reservation_id)
    if reservation.user_id != session['user_id'] or reservation.end_time:
        flash('No active reservation found!')
        return redirect(url_for('user_dashboard'))
    reservation.end_time = datetime.now()
    reservation.total_time = (reservation.end_time - reservation.start_time).total_seconds() / 60   # in minutes
    reservation.cost = round(10 * (reservation.total_time / 60), 2) # Rs 10/hour
    spot = ParkingSpot.query.get(reservation.spot_id)
    spot.status = 'EMPTY'
    db.session.commit()
    flash(f'Spot released! Time used: {reservation.total_time:.2f} min. Amount due: Rs {reservation.cost}')
    return redirect(url_for('user_dashboard'))

@app.route('/parking_history')
def parking_history():
    if not session.get('user_id'):
        return redirect(url_for('user_login'))
    reservations = Reservation.query.filter_by(user_id=session['user_id']).all()
    return render_template('parking_history.html', reservations=reservations)

if __name__ == '__main__':
    app.run(debug=True)
