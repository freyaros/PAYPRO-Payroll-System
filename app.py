from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'nexaverse_payroll_super_secret_key' 

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',         
        password='root', # Make sure to change this to your actual MySQL password!
        database='EmployeeManagement'
    )

# --- PUBLIC ROUTES ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

# --- AUTHENTICATION & MULTI-SESSION CHECK-IN ---
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
            if user.get('role') == 'HR':
                flash('You are an HR Admin. Please use the HR Admin Portal.')
                return redirect(url_for('employee_login'))
                
            session['loggedin'] = True
            session['employee_id'] = user['employee_id']
            session['first_name'] = user['first_name']
            session['role'] = 'Employee'
            
            # AUTOMATED CHECK-IN (Forces a new session row every time they log in)
            today_date = datetime.today().strftime('%Y-%m-%d')
            current_time = datetime.now().strftime('%H:%M:%S')
            
            cursor.execute("INSERT INTO Attendance (employee_id, date, check_in) VALUES (%s, %s, %s)", (emp_id, today_date, current_time))
            conn.commit()
            
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
        emp_id = request.form['employee_id'] 
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        job_title = request.form['job_title']
        contact = request.form['contact']
        hashed_password = generate_password_hash(request.form['password'])

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO Employee (employee_id, first_name, last_name, dob, gender, job_title, contact, password, role) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Employee')
            """, (emp_id, first_name, last_name, dob, gender, job_title, contact, hashed_password))
            conn.commit()
            
            if session.get('loggedin') and session.get('role') == 'HR':
                flash(f'New employee ({first_name} {last_name}) added successfully!')
                return redirect(url_for('admin_employees'))
            else:
                flash('Registration successful! You can now login.')
                return redirect(url_for('employee_login'))
        except mysql.connector.IntegrityError:
            flash('Error: That Employee ID is already taken.')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')

@app.route('/hr_register', methods=['GET', 'POST'])
def hr_register():
    if request.method == 'POST':
        emp_id = request.form['employee_id'] 
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        dob = request.form['dob']
        gender = request.form['gender']
        job_title = request.form['job_title']
        contact = request.form['contact']
        hashed_password = generate_password_hash(request.form['password'])

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
        hashed_password = generate_password_hash(new_password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE Employee SET password = %s WHERE employee_id = %s", (hashed_password, session['reset_emp_id']))
        conn.commit()
        cursor.close()
        conn.close()
        
        session.pop('reset_emp_id', None)
        flash('Password Reset Successful! You may now log in.')
        return redirect(url_for('index'))
    return render_template('reset_password.html')

# --- AUTOMATED CHECK-OUT & MULTI-SESSION MATH ---
@app.route('/logout')
def logout():
    if session.get('loggedin') and session.get('role') == 'Employee':
        emp_id = session['employee_id']
        today_date = datetime.today().strftime('%Y-%m-%d')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Grab the MOST RECENT check-in that doesn't have a check-out yet
        cursor.execute("""
            SELECT check_in FROM Attendance 
            WHERE employee_id = %s AND date = %s AND (check_out IS NULL OR check_out = '') 
            ORDER BY check_in DESC LIMIT 1
        """, (emp_id, today_date))
        record = cursor.fetchone()
        
        if record and record['check_in']:
            try:
                check_in_str = str(record['check_in']) 
                
                if len(check_in_str) > 5:
                    t1 = datetime.strptime(check_in_str, '%H:%M:%S')
                else:
                    t1 = datetime.strptime(check_in_str, '%H:%M')
                
                now = datetime.now()
                checkout_time_str = now.strftime('%H:%M:%S')
                t2 = datetime.strptime(checkout_time_str, '%H:%M:%S')
                
                if t2 < t1:
                    total_hours = 0.0
                else:
                    total_hours = round((t2 - t1).total_seconds() / 3600, 2)
                    
                # Update ONLY that exact session row using the matching check_in time
                cursor.execute("""
                    UPDATE Attendance 
                    SET check_out = %s, total_hours = %s 
                    WHERE employee_id = %s AND date = %s AND check_in = %s
                """, (checkout_time_str, total_hours, emp_id, today_date, record['check_in']))
                conn.commit()
            except Exception as e:
                print(f"Attendance Math Error: {e}")
                
        cursor.close()
        conn.close()

    session.clear()
    return redirect(url_for('index'))

# --- EMPLOYEE DASHBOARD ROUTES ---
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session or session.get('role') != 'Employee': return redirect(url_for('employee_login'))
    return render_template('dashboard.html', first_name=session['first_name'])

@app.route('/attendance')
def attendance():
    if 'loggedin' not in session: return redirect(url_for('employee_login'))
    emp_id = session['employee_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Attendance WHERE employee_id = %s ORDER BY date DESC, check_in DESC", (emp_id,))
    records = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('attendance.html', records=records)

@app.route('/salary')
def salary():
    if 'loggedin' not in session: return redirect(url_for('employee_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
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

@app.route('/admin/employees')
def admin_employees():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Employee WHERE role = 'Employee' ORDER BY employee_id DESC")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_employees.html', employees=employees)

@app.route('/admin/delete_employee/<int:emp_id>')
def delete_employee(emp_id):
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Employee WHERE employee_id = %s", (emp_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Employee record deleted successfully.')
    return redirect(url_for('admin_employees'))

@app.route('/admin/payroll', methods=['GET', 'POST'])
def admin_payroll():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        emp_id = request.form['employee_id']
        pay_period = request.form['pay_period']
        base_pay = float(request.form['base_pay'])
        allowances = float(request.form['allowances'])
        bonuses = float(request.form['bonuses'])
        standard_deductions = float(request.form['deductions'])
        tax = float(request.form['tax'])
        
        # Fetch approved leaves from database
        cursor.execute("SELECT start_date, end_date FROM Leave_Table WHERE employee_id = %s AND status = 'Approved'", (emp_id,))
        approved_leaves = cursor.fetchall()
        
        total_leave_days = 0
        for leave in approved_leaves:
            try:
                if isinstance(leave['start_date'], str):
                    start = datetime.strptime(leave['start_date'], '%Y-%m-%d')
                    end = datetime.strptime(leave['end_date'], '%Y-%m-%d')
                else:
                    start = leave['start_date']
                    end = leave['end_date']
                days = (end - start).days + 1 
                total_leave_days += days
            except Exception as e:
                pass
        
        # --- NEW DYNAMIC LOP CALCULATION LOGIC ---
        
        # Convert total leave days to hours (assuming an 8-hour workday)
        hours_absent = total_leave_days * 8
        
        # Step 1: Calculate Monthly Gross
        monthly_gross_salary = base_pay + allowances + bonuses
        
        # Step 2: Convert to Annual Salary
        annual_salary = monthly_gross_salary * 12
        
        # Step 3: Calculate Weekly Salary
        weekly_salary = annual_salary / 52
        
        # Step 4: Determine Hourly Rate
        hourly_rate = weekly_salary / 40
        
        # Step 5: Calculate Total LOP Deduction
        total_lop_deduction = hourly_rate * hours_absent
        
        # Final Net Pay Math (Gross minus standard deductions, tax, and the new LOP penalty)
        total_combined_deductions = standard_deductions + tax + total_lop_deduction
        net_monthly_pay = monthly_gross_salary - total_combined_deductions
        
        pay_date = datetime.today().strftime('%Y-%m-%d')
        
        # Insert the finalized payroll data into the database
        cursor.execute("""
            INSERT INTO Salary (employee_id, pay_period, base_pay, allowances, bonuses, deductions, tax, net_pay, status, pay_date) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Paid', %s)
        """, (emp_id, pay_period, base_pay, allowances, bonuses, (standard_deductions + total_lop_deduction), tax, net_monthly_pay, pay_date))
        conn.commit()
        
        # Flash message updated to show the exact dynamic breakdown!
        flash(f'Salary processed! LOP Deduction: ${total_lop_deduction:.2f} ({hours_absent} hrs at ${hourly_rate:.2f}/hr). Final Net Pay: ${net_monthly_pay:.2f}')
        return redirect(url_for('admin_payroll'))
        
    cursor.execute("SELECT employee_id, first_name, last_name FROM Employee WHERE role = 'Employee'")
    employees = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('admin_payroll.html', employees=employees)

@app.route('/admin/leaves', methods=['GET', 'POST'])
def admin_leaves():
    if 'loggedin' not in session or session.get('role') != 'HR': return redirect(url_for('hr_login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        leave_id = request.form['leave_id']
        action = request.form['action']
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