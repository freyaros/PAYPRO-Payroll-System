#  PAYPRO: Enterprise-Grade Indian Payroll & HR Management System

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-lightgrey.svg)
![MySQL](https://img.shields.io/badge/MySQL-Database-orange.svg)
![Security](https://img.shields.io/badge/Security-IDOR%20Protected-green.svg)

**PAYPRO** is a secure, localized, and fully automated Human Resources and Payroll management system tailored for the Indian IT sector. Built as a comprehensive Database Management System (DBMS) project, it moves beyond basic CRUD operations by utilizing advanced SQL features like Autonomous Event Schedulers, Triggers, and Smart Balance Verification.

##  Table of Contents
- [Project Overview](#-project-overview)
- [Advanced DBMS Features (The X-Factors)](#-advanced-dbms-features-the-x-factors)
- [Core Functionalities](#-core-functionalities)
- [Security & Localization](#-security--localization)
- [Tech Stack](#-tech-stack)
- [Installation & Setup](#-installation--setup)

---

##  Project Overview
PAYPRO serves two primary user roles: **Employees** and **HR Administrators**. 
It handles the complete employee lifecycle: from secure onboarding and automated time-tracking to leave management and smart CTC (Cost to Company) salary calculations. The user interface features a premium, responsive "Glassmorphism" dark theme.

##  Advanced DBMS Features (The "X-Factors")
This project leverages deep database architecture to automate business logic at the engine level:
* **Autonomous Event Schedulers:** A MySQL background event automatically credits 1 Casual Leave (CL) and 1 Paid Leave (PL) to all active employees on the 1st of every month at midnight, requiring zero Python server interaction.
* **Smart Balance Verification:** SQL transactional logic prevents HR from approving leaves if the employee's specific balance (CL or PL) is insufficient.
* **Database Triggers:** Automated SQL triggers monitor specific table insertions/updates (e.g., preventing underage registrations or logging password changes).

##  Core Functionalities

### For Employees:
* **Automated Attendance:** A multi-session timer automatically tracks and logs daily "logged-in" seconds.
* **Leave Management:** Apply for Casual, Paid, or Unpaid leaves and track real-time balances.
* **Fintech Payslip Portal:** View dynamic, generated payslips breaking down Base Pay, Allowances (HRA/TA), Performance Bonuses, and LOP (Loss of Pay) deductions, complete with a Print-to-PDF feature.

### For HR Administrators:
* **Smart Auto-Calculating Payroll:** HR inputs the Basic Salary, and the frontend JS instantly calculates standard Indian IT Allowances (50% HRA) and Bonuses. The backend automatically queries "Unpaid" leaves to deduct precise LOP penalties.
* **Employee Onboarding:** Review and approve incoming join requests to generate sequential Employee IDs.
* **Leave Adjudication:** Approve or reject leaves with automatic balance deductions.

##  Security & Localization
* **IDOR Protection (The Gatekeeper):** Public users are blocked from registering as Administrators. HR registration requires a hardcoded "Company Master Token".
* **Cryptographic Hashing:** All passwords are hashed using `Werkzeug` security before entering the database.
* **Strict Password Policies:** Custom Regex enforces mandatory uppercase, lowercase, numeric, and special characters across all creation and reset routes.
* **Indian Localization:** Enforces strict 10-digit Indian mobile numbers (starting with 6-9), utilizes INR (₹) formatting globally, and features an Indian HQ.

##  Tech Stack
* **Backend:** Python 3, Flask, Werkzeug
* **Database:** MySQL (mysql-connector-python)
* **Frontend:** HTML5, CSS3 (Glassmorphism), Vanilla JavaScript
* **Architecture:** Monolithic MVC

##  Installation & Setup

**1. Clone the repository**
```bash
git clone [https://github.com/freyaros/PAYPRO-Payroll-System](https://github.com/freyaros/PAYPRO-Payroll-System)
cd PAYPRO