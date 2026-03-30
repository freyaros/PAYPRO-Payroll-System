from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import json
app = Flask(__name__)
app.secret_key = 'nexaverse_payroll_super_secret_key' 

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',         
        password='root', # Make sure to change this to your actual MySQL password!
        database='EmployeeManagement'
    )

def check_password_strength(password):
    """Returns True if password is strong, False otherwise."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    if not re.search(r"[@$!%*?&#]", password):
        return False, "Password must contain at least one special character (@$!%*?&#)."
    return True, "Password is strong."

def is_valid_indian_mobile(mobile):
    """Returns True if it's a valid 10-digit Indian mobile number."""
    return bool(re.match(r"^[6-9]\d{9}$", mobile))

# --- PUBLIC ROUTES ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact(): 
    if request.method == 'POST':
        # Grab the user's name from the form
        name = request.form.get('name', 'Guest')
        
        # In a real app, you would save this to the DB or email it to HR.
        # For now, we just flash a success message!
        flash(f'Thank you, {name}! Your message has been sent to our support team.')
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

@app.route('/admin/accrue_leaves')
def admin_accrue_leaves():
    if 'loggedin' not in session or session.get('role') != 'HR': 
        return redirect(url_for('hr_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Employee SET cl_balance = cl_balance + 1, pl_balance = pl_balance + 1 WHERE role = 'Employee'")
    conn.commit()
    cursor.close()
    conn.close()
    
    # NEW FLASH MESSAGE
    flash('Manual Override Complete: +1 CL and +1 PL distributed. (Note: The database also does this automatically on the 1st of every month).')
    return redirect(url_for('admin_leaves'))

# --- AUTHENTICATION & MULTI-SESSION CHECK-IN ---
from datetime import datetime # Ensure this is at the very top of your app.py file

@app.route('/employee_login', methods=['GET', 'POST'])
def employee_login():
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (emp_id,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            # Block HR from using the Employee login
            if user.get('role') == 'HR':
                flash('You are an HR Admin. Please use the HR Admin Portal.')
                return redirect(url_for('employee_login'))
                
            # Set up the secure session
            session['loggedin'] = True
            session['employee_id'] = user['employee_id']
            session['first_name'] = user['first_name']
            session['role'] = 'Employee'
            
            # --- NEW: AUTOMATED ATTENDANCE TIMER LOGIC ---
            today_date = datetime.today().strftime('%Y-%m-%d')
            now = datetime.now() # Gets exact current date and time
            
            # Check if they already logged in today
            cursor.execute("SELECT * FROM Attendance WHERE employee_id = %s AND work_date = %s", (emp_id, today_date))
            att = cursor.fetchone()
            
            if not att:
                # First login of the day: Create the row, start the timer, AND record check_in
                cursor.execute(
                    "INSERT INTO Attendance (employee_id, work_date, check_in, last_login, total_seconds) VALUES (%s, %s, %s, %s, 0)", 
                    (emp_id, today_date, now, now)
                )
            else:
                # Logging back in: Just update last_login to resume the timer! 
                # (We do NOT update check_in here, because we want to keep their original morning start time)
                cursor.execute("UPDATE Attendance SET last_login = %s WHERE attendance_id = %s", (now, att['attendance_id']))
                
            conn.commit()
            # ---------------------------------------------
            
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect Employee ID or Password!')
            cursor.close()
            conn.close()
            
    return render_template('employee_login.html')
@app.route('/hr_login', methods=['GET', 'POST'])
def hr_login():
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Employee WHERE employee_id = %s", (emp_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            if user.get('role') != 'HR':
                flash('Access Denied. You do not have HR privileges.')
                return redirect(url_for('hr_login'))
                
            session['loggedin'] = True
            session['employee_id'] = user['employee_id']
            session['first_name'] = user['first_name']
            session['role'] = 'HR'
            return redirect(url_for('hr_dashboard'))
        else:
            flash('Incorrect HR ID or Password!')
    return render_template('hr_login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        job_title = request.form['job_title']
        contact = request.form['contact']

        # Validate Indian Mobile Number (10 digits starting with 6-9)
        if not is_valid_indian_mobile(contact):
            flash('Invalid Contact! Must be a 10-digit Indian mobile number starting with 6-9.')
            return redirect(url_for('register'))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Join_Requests (first_name, last_name, dob, gender, job_title, contact) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (first_name, last_name, dob, gender, job_title, contact))
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Join Request sent to HR! You will receive your Employee ID and password once approved.')
        return redirect(url_for('employee_login'))
    return render_template('register.html')

@app.route('/hr_register', methods=['GET', 'POST'])
def hr_register():
    if request.method == 'POST':
        # --- 1. THE SECURITY GATEKEEPER ---
        SECRET_COMPANY_TOKEN = "NEXA-ADMIN-2026"
        submitted_token = request.form.get('company_token')
        
        if submitted_token != SECRET_COMPANY_TOKEN:
            flash('SECURITY ALERT: Invalid Company Master Token. Access Denied.')
            return redirect(url_for('hr_register'))

        # --- 2. THE PASSWORD STRENGTH CHECKER ---
        raw_password = request.form['password']
        is_strong, msg = check_password_strength(raw_password)
        
        if not is_strong:
            flash(f'Security Error: {msg}')
            return redirect(url_for('hr_register'))
        # ----------------------------------------

        emp_id = request.form['employee_id'] 
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        job_title = request.form['job_title']
        contact = request.form['contact']
        
        # Hash the validated password!
        hashed_password = generate_password_hash(raw_password)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Employee (employee_id, first_name, last_name, dob, gender, job_title, contact, password, role) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'HR')
            """, (emp_id, first_name, last_name, dob, gender, job_title, contact, hashed_password))
            conn.commit()
            flash('HR Registration successful! Welcome to the Admin team.')
            return redirect(url_for('hr_login'))
        except mysql.connector.IntegrityError:
            flash('Error: That Admin ID is already taken.')
        finally:
            cursor.close()
            conn.close()
            
    return render_template('hr_register.html')

# --- PASSWORD RECOVERY ---
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        dob = request.form['dob'] 
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Employee WHERE employee_id = %s AND dob = %s", (emp_id, dob))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['reset_emp_id'] = emp_id 
            return redirect(url_for('reset_password'))
        else:
            flash('Verification Failed: Incorrect ID or Date of Birth.')
    return render_template('forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if 'reset_emp_id' not in session:
        return redirect(url_for('forgot_password'))
        
    if request.method == 'POST':
        new_password = request.form['password']
        
        # --- THE FINAL SECURITY LOCKDOWN ---
        is_strong, msg = check_password_strength(new_password)
        if not is_strong:
            flash(f'Security Error: {msg}')
            return redirect(url_for('reset_password'))
        # -----------------------------------
        
        hashed_password = generate_password_hash(new_password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Employee SET password = %s WHERE employee_id = %s", (hashed_password, session['reset_emp_id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        session.pop('reset_emp_id', None)
        flash('Password Reset Successful! You may now log in.')
        return redirect(url_for('index'))  # Or employee_login
        
    return render_template('reset_password.html')

# --- AUTOMATED CHECK-OUT & MULTI-SESSION MATH ---
@app.route('/logout')
def logout():
    # 1. Save the role into a variable BEFORE clearing the session
    user_role = session.get('role')

    # --- PAUSE ATTENDANCE TIMER (Only for Employees) ---
    if 'loggedin' in session and user_role == 'Employee':
        emp_id = session['employee_id']
        today = datetime.today().strftime('%Y-%m-%d')
        now = datetime.now()
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Attendance WHERE employee_id = %s AND work_date = %s AND last_login IS NOT NULL", (emp_id, today))
        att = cursor.fetchone()
        
        if att:
            # Calculate time spent logged in during this session
            time_diff = now - att['last_login']
            seconds_worked = int(time_diff.total_seconds())
            new_total = att['total_seconds'] + seconds_worked
            
            # Update total, pause timer, and record check_out time
            cursor.execute(
                "UPDATE Attendance SET total_seconds = %s, last_login = NULL, check_out = %s WHERE attendance_id = %s", 
                (new_total, now, att['attendance_id'])
            )
            conn.commit()
            
        cursor.close()
        conn.close()
    # -----------------------------------
    
    # 2. Now it is safe to clear the session
    session.clear()

    # 3. Route them to the correct login page based on the saved variable
    if user_role == 'HR':
        # NOTE: Make sure 'hr_login' exactly matches the name of your HR login route!
        return redirect(url_for('hr_login')) 
    else:
        return redirect(url_for('employee_login'))
    
# --- EMPLOYEE DASHBOARD ROUTES ---
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'Employee': 
        return redirect(url_for('employee_login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch Attendance (your existing timer code)
    today = datetime.today().strftime('%Y-%m-%d')
    cursor.execute("SELECT total_seconds, last_login FROM Attendance WHERE employee_id = %s AND work_date = %s", (session['employee_id'], today))
    att_data = cursor.fetchone()
    
    current_total_seconds = 0
    if att_data:
        current_total_seconds = att_data['total_seconds']
        if att_data['last_login']:
            session_seconds = int((datetime.now() - att_data['last_login']).total_seconds())
            current_total_seconds += session_seconds

    # --- NEW: 2. Fetch Leave Balances ---
    cursor.execute("SELECT cl_balance, pl_balance FROM Employee WHERE employee_id = %s", (session['employee_id'],))
    emp_data = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    # Pass the balances to the template
    return render_template('dashboard.html', 
                           first_name=session['first_name'], 
                           worked_seconds=current_total_seconds,
                           cl_balance=emp_data['cl_balance'],
                           pl_balance=emp_data['pl_balance'])
@app.route('/attendance')
def attendance():
    if 'loggedin' not in session: return redirect(url_for('employee_login'))
    emp_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Attendance WHERE employee_id = %s ORDER BY work_date DESC, last_login DESC", (emp_id,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('attendance.html', attendance_records=records)

@app.route('/salary')
def salary():
    if 'loggedin' not in session or session.get('role') != 'Employee': 
        return redirect(url_for('employee_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Fetch all salary records for this specific employee, newest first
    cursor.execute("SELECT * FROM Salary WHERE employee_id = %s ORDER BY pay_date DESC", (session['employee_id'],))
    records = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('salary.html', records=records)

@app.route('/leave', methods=['GET', 'POST'])
def leave():
    if 'loggedin' not in session: return redirect(url_for('employee_login'))
    emp_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        leave_type = request.form['leave_type']
        start_date = request.form['start_date']
        end_date = request.form['end_date']
        cursor.execute("INSERT INTO Leave_Table (employee_id, leave_type, start_date, end_date, status) VALUES (%s, %s, %s, %s, %s)", (emp_id, leave_type, start_date, end_date, 'Pending'))
        conn.commit()
        flash('Leave request submitted successfully!')
        return redirect(url_for('leave'))
        
    cursor.execute("SELECT * FROM Leave_Table WHERE employee_id = %s ORDER BY start_date DESC", (emp_id,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('leave.html', records=records)

# --- HR ADMIN ROUTES ---
@app.route('/hr_dashboard')
def hr_dashboard():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    return render_template('hr_dashboard.html', first_name=session['first_name'])

@app.route('/admin/employees', methods=['GET', 'POST'])
def admin_employees():
    if 'loggedin' not in session or session.get('role') != 'HR': 
        return redirect(url_for('hr_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # --- 1. HANDLING APPROVALS (Your exact POST logic) ---
    if request.method == 'POST':
        req_id = request.form.get('request_id')
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        job_title = request.form['job_title']
        contact = request.form['contact']
        initial_password = request.form['initial_password'] 
        
        # Check Password Strength for HR
        is_strong, msg = check_password_strength(initial_password)
        if not is_strong:
            flash(f'Cannot add employee. Initial Password Error: {msg}')
            return redirect(url_for('admin_employees'))
            
        hashed_password = generate_password_hash(initial_password)
        
        try:
            # Attempt to insert into Employee
            cursor.execute("""
                INSERT INTO Employee (first_name, last_name, dob, gender, job_title, contact, password, role) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Employee')
            """, (first_name, last_name, dob, gender, job_title, contact, hashed_password))
            
            # Mark request as approved
            if req_id:
                cursor.execute("UPDATE Join_Requests SET status = 'Approved' WHERE request_id = %s", (req_id,))
                
            conn.commit()
            flash('Employee added successfully! Their initial password is set.')
            
        except mysql.connector.Error as err:
            # THIS CATCHES OUR CUSTOM DBMS TRIGGER ERROR!
            flash(f'{err.msg}') 
            
        return redirect(url_for('admin_employees'))
        
    # --- 2. GET REQUEST: FETCH DATA & PREDICT IDs ---
    cursor.execute("SELECT * FROM Employee WHERE role = 'Employee' ORDER BY employee_id DESC")
    employees = cursor.fetchall()
    
    # Predict the next Employee ID
    cursor.execute("SELECT MAX(CAST(employee_id AS UNSIGNED)) AS max_id FROM Employee")
    result = cursor.fetchone()
    next_available_id = (result['max_id'] or 1000) + 1 
    
    # Fetch pending requests
    cursor.execute("SELECT * FROM Join_Requests WHERE status = 'Pending' ORDER BY request_date ASC")
    pending_requests = cursor.fetchall()
    
    # Assign predicted_id for the frontend
    for req in pending_requests:
        req['predicted_id'] = next_available_id
        next_available_id += 1 
        
    cursor.close()
    conn.close()
    return render_template('admin_employees.html', employees=employees, requests=pending_requests)


# --- THE NEW DECLINE ROUTE ---
@app.route('/admin/decline_request/<int:request_id>', methods=['POST'])
def decline_request(request_id):
    if 'loggedin' not in session or session.get('role') != 'HR': 
        return redirect(url_for('hr_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM Join_Requests WHERE request_id = %s", (request_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    flash('Join request declined and securely removed.')
    return redirect(url_for('admin_employees'))

# --- ROUTE TO REMOVE AN ACTIVE EMPLOYEE ---
@app.route('/admin/delete_employee/<int:emp_id>')
def delete_employee(emp_id):
    # Security check: Only HR can delete employees
    if 'loggedin' not in session or session.get('role') != 'HR': 
        return redirect(url_for('hr_login'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Securely delete the employee from the database
        cursor.execute("DELETE FROM Employee WHERE employee_id = %s", (emp_id,))
        conn.commit()
        flash(f'Employee EMP-{emp_id} has been securely removed from the system.')
    except Exception as e:
        # Just in case they are tied to other tables and can't be deleted easily
        flash(f'Error removing employee: {str(e)}')
    finally:
        cursor.close()
        conn.close()
        
    return redirect(url_for('admin_employees'))

@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if 'loggedin' not in session: return redirect(url_for('index'))
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        
        # --- NEW: Check Password Strength ---
        is_strong, msg = check_password_strength(new_password)
        if not is_strong:
            flash(f'Security Error: {msg}')
            return redirect(url_for('change_password'))
        # ------------------------------------
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT password FROM Employee WHERE employee_id = %s", (session['employee_id'],))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], current_password):
            hashed_new = generate_password_hash(new_password)
            # The database Trigger we made will automatically detect this UPDATE!
            cursor.execute("UPDATE Employee SET password = %s WHERE employee_id = %s", (hashed_new, session['employee_id']))
            conn.commit()
            flash('Password updated successfully! Event logged by database trigger.')
        else:
            flash('Incorrect current password.')
            
        cursor.close()
        conn.close()
        return redirect(url_for('change_password'))
        
    return render_template('change_password.html')



@app.route('/admin/payroll', methods=['GET', 'POST'])
def admin_payroll():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        pay_period = request.form['pay_period']
        base_pay = float(request.form['base_pay'])
        
        # 1. AUTO-CALCULATE BASED ON INDIAN IT CTC STRUCTURE
        # Allowances: 50% of Basic (HRA) + ₹1600 (TA)
        allowances = (base_pay * 0.50) + 1600
        # Bonuses: 25% of Basic (Equates to approx 10% of total CTC)
        bonuses = base_pay * 0.25 
        
        # 2. Fetch ONLY "Unpaid" approved leaves for LOP
        cursor.execute("SELECT start_date, end_date FROM Leave_Table WHERE employee_id = %s AND status = 'Approved' AND leave_type = 'Unpaid'", (emp_id,))
        approved_leaves = cursor.fetchall()
        
        total_leave_days = 0
        for leave in approved_leaves:
            start = datetime.strptime(str(leave['start_date']), '%Y-%m-%d')
            end = datetime.strptime(str(leave['end_date']), '%Y-%m-%d')
            total_leave_days += (end - start).days + 1 
            
        # 3. Calculate LOP Deductions
        hours_absent = total_leave_days * 8
        monthly_gross_salary = base_pay + allowances + bonuses
        hourly_rate = (monthly_gross_salary * 12) / 52 / 40
        total_lop_deduction = hourly_rate * hours_absent
        
        # 4. Final Net Pay (No Tax!)
        net_monthly_pay = monthly_gross_salary - total_lop_deduction
        pay_date = datetime.today().strftime('%Y-%m-%d')
        
        # Insert into database (Notice we removed the 'tax' column here!)
        cursor.execute("""
            INSERT INTO Salary (employee_id, pay_period, base_pay, allowances, bonuses, deductions, net_pay, status, pay_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'Paid', %s)
        """, (emp_id, pay_period, base_pay, allowances, bonuses, total_lop_deduction, net_monthly_pay, pay_date))
        conn.commit()
        
        flash(f'Salary processed! LOP Deduction: ₹{total_lop_deduction:.2f}. Final Net Pay: ₹{net_monthly_pay:.2f}')
        return redirect(url_for('admin_payroll'))
        
    # --- GET REQUEST: PREPARE DATA FOR THE FRONTEND ---
    cursor.execute("SELECT employee_id, first_name, last_name FROM Employee WHERE role = 'Employee'")
    employees = cursor.fetchall()
    
    # Build a dictionary of LOP Hours for every employee so JavaScript can use it instantly
    emp_lop_hours = {}
    for emp in employees:
        cursor.execute("SELECT start_date, end_date FROM Leave_Table WHERE employee_id = %s AND status = 'Approved' AND leave_type = 'Unpaid'", (emp['employee_id'],))
        leaves = cursor.fetchall()
        days = 0
        for l in leaves:
            start = datetime.strptime(str(l['start_date']), '%Y-%m-%d')
            end = datetime.strptime(str(l['end_date']), '%Y-%m-%d')
            days += (end - start).days + 1
        emp_lop_hours[emp['employee_id']] = days * 8
        
    cursor.close()
    conn.close()
    
    # We pass the dictionary to HTML as a JSON string
    return render_template('admin_payroll.html', employees=employees, lop_data=json.dumps(emp_lop_hours))

@app.route('/admin/leaves', methods=['GET', 'POST'])
def admin_leaves():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        leave_id = request.form['leave_id']
        action = request.form['action'] # Will be 'Approved' or 'Rejected'
        
        if action == 'Approved':
            # 1. Get the leave details
            cursor.execute("SELECT * FROM Leave_Table WHERE leave_id = %s", (leave_id,))
            leave = cursor.fetchone()
            
            # 2. Get the employee's current balances
            cursor.execute("SELECT cl_balance, pl_balance FROM Employee WHERE employee_id = %s", (leave['employee_id'],))
            emp = cursor.fetchone()
            
            # 3. Calculate how many days they requested
            start = datetime.strptime(str(leave['start_date']), '%Y-%m-%d')
            end = datetime.strptime(str(leave['end_date']), '%Y-%m-%d')
            requested_days = (end - start).days + 1
            
            # 4. Smart Balance Verification & Deduction
            if leave['leave_type'] == 'Casual':
                if emp['cl_balance'] >= requested_days:
                    cursor.execute("UPDATE Employee SET cl_balance = cl_balance - %s WHERE employee_id = %s", (requested_days, leave['employee_id']))
                else:
                    flash(f"Approval Failed! Employee only has {emp['cl_balance']} Casual Leaves left.")
                    return redirect(url_for('admin_leaves'))
                    
            elif leave['leave_type'] == 'Paid':
                if emp['pl_balance'] >= requested_days:
                    cursor.execute("UPDATE Employee SET pl_balance = pl_balance - %s WHERE employee_id = %s", (requested_days, leave['employee_id']))
                else:
                    flash(f"Approval Failed! Employee only has {emp['pl_balance']} Paid Leaves left.")
                    return redirect(url_for('admin_leaves'))
                    
        # 5. Finally, update the status (Approved or Rejected)
        cursor.execute("UPDATE Leave_Table SET status = %s WHERE leave_id = %s", (action, leave_id))
        conn.commit()
        flash(f'Leave {action} successfully!')
        return redirect(url_for('admin_leaves'))
        
    cursor.execute("""
        SELECT l.*, e.first_name, e.last_name 
        FROM Leave_Table l 
        JOIN Employee e ON l.employee_id = e.employee_id 
        ORDER BY l.start_date DESC
    """)
    all_leaves = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_leaves.html', leaves=all_leaves)

@app.route('/admin/reports')
def admin_reports():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) as count FROM Employee WHERE role='Employee'")
    emp_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT SUM(net_pay) as total FROM Salary WHERE status='Paid'")
    total_salary = cursor.fetchone()['total'] or 0.00
    
    cursor.execute("SELECT COUNT(*) as count FROM Leave_Table WHERE status='Pending'")
    pending_leaves = cursor.fetchone()['count']
    
    cursor.execute("""
        SELECT s.pay_date, s.pay_period, s.net_pay, e.first_name, e.last_name 
        FROM Salary s JOIN Employee e ON s.employee_id = e.employee_id ORDER BY s.pay_date DESC LIMIT 10
    """)
    recent_payouts = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_reports.html', emp_count=emp_count, total_salary=total_salary, pending_leaves=pending_leaves, payouts=recent_payouts)

@app.route('/admin/settings')
def admin_settings():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    return render_template('admin_settings.html')

if __name__ == '__main__':
    app.run(debug=True)