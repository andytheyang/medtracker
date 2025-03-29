import os
import json
from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = os.urandom(24) # Needed for flashing messages (like confirmation)

STATE_FILE = 'state.json'
LOG_FILE = 'log.txt'

# Define the medicines
MEDICINES = {
    'morning_magnesium': 'Morning Magnesium',
    'morning_flonase': 'Morning Flonase',
    'evening_magnesium': 'Evening Magnesium'
}

# --- State Management ---

def get_today_date_str():
    """Returns today's date as YYYY-MM-DD string."""
    return date.today().isoformat()

def load_state():
    """Loads state from file, resets if date is old."""
    today_str = get_today_date_str()
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
            # Check if the state is for today
            if state.get('date') == today_str:
                # Ensure all expected keys are present
                for med_id in MEDICINES:
                    if med_id not in state:
                        state[med_id] = False
                return state
            else:
                # Date mismatch, reset for today
                print(f"Date changed from {state.get('date')} to {today_str}. Resetting state.")
                return reset_state_file()
        else:
            # File doesn't exist, create initial state for today
            print("State file not found. Creating initial state.")
            return reset_state_file()
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading state file: {e}. Resetting state.")
        return reset_state_file() # Reset if file is corrupt or unreadable

def save_state(state):
    """Saves the current state to the file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
    except IOError as e:
        print(f"Error saving state file: {e}")

def reset_state_file():
    """Creates a new, default state for today and saves it."""
    today_str = get_today_date_str()
    initial_state = {'date': today_str}
    for med_id in MEDICINES:
        initial_state[med_id] = False
    save_state(initial_state)
    return initial_state

# --- Logging ---

def log_action(action_description):
    """Appends an action to the log file with a timestamp."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{now} - {action_description}\n"
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(log_entry)
    except IOError as e:
        print(f"Error writing to log file: {e}")

def read_log(limit=50):
    """Reads the last 'limit' lines from the log file."""
    if not os.path.exists(LOG_FILE):
        return []
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
        # Return the last 'limit' lines in reverse order (most recent first)
        return [line.strip() for line in reversed(lines[-limit:])]
    except IOError as e:
        print(f"Error reading log file: {e}")
        return ["Error reading log file."]

# --- Flask Routes ---

@app.route('/')
def index():
    """Main page: displays buttons and history."""
    current_state = load_state() # This also handles the midnight reset check
    history = read_log()
    return render_template('index.html',
                           state=current_state,
                           history=history,
                           medicines=MEDICINES,
                           today_date=date.today().strftime('%A, %B %d, %Y'))

@app.route('/take/<medicine_id>', methods=['POST'])
def take_medicine(medicine_id):
    """Handles marking a medicine as taken."""
    if medicine_id not in MEDICINES:
        flash("Invalid medicine ID.", "error")
        return redirect(url_for('index'))

    current_state = load_state() # Ensure we have today's state

    if not current_state.get(medicine_id, False): # Only log if not already taken
        current_state[medicine_id] = True
        action = f"Took {MEDICINES[medicine_id]}"
        log_action(action)
        save_state(current_state)
        flash(f"{MEDICINES[medicine_id]} marked as taken!", "success")
    else:
        flash(f"{MEDICINES[medicine_id]} was already marked as taken.", "info")

    return redirect(url_for('index'))

@app.route('/reset_today', methods=['POST'])
def reset_today():
    """Resets all medicine states for the current day."""
    current_state = load_state() # Load state to get today's date correctly
    today_str = current_state['date'] # Use date from loaded state

    # Create a new reset state for today
    reset_state = {'date': today_str}
    for med_id in MEDICINES:
        reset_state[med_id] = False

    save_state(reset_state) # Save the reset state
    log_action("Reset button clicked for today.")
    flash("Today's medicine status has been reset.", "warning")
    return redirect(url_for('index'))

# --- Run the App ---

if __name__ == '__main__':
    print("Starting Medicine Tracker server...")
    print("Access it at http://127.0.0.1:5000/ or http://[your-ip-address]:5000/")
    # Use host='0.0.0.0' to make it accessible on your network
    app.run(host='0.0.0.0', port=5000, debug=False)
    # Turn debug=False for regular use, True for development