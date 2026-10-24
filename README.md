# 💰 FinanceFlow — Personal Expense Tracker

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Framework-Flask%203.1-black.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Excel](https://img.shields.io/badge/Spreadsheets-openpyxl-217346.svg?logo=microsoftexcel&logoColor=white)](https://openpyxl.readthedocs.io/)
[![TailwindCSS](https://img.shields.io/badge/UI-TailwindCSS-06B6D4.svg?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Chart.js](https://img.shields.io/badge/Charts-Chart.js%204-FF6384.svg?logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![Responsive](https://img.shields.io/badge/Device-Mobile%20%7C%20Tablet%20%7C%20Desktop-teal.svg)](#-multi-device-responsive-design)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**A sleek, responsive, and full-featured Personal Expense Tracker built with Python, SQLite, and Excel.**  
Track daily spending, categorize transactions, set category budgets, explore visual monthly reports, and export executive multi-sheet Excel reports — across **Mobile**, **Tablet**, and **Desktop** browsers.

</div>

---

## 📸 Key Highlights

- 🏛️ **Multi-Bank Accounts & Combined Net Balance**: Add different bank accounts (e.g. *Main Checking, High-Yield Savings, Digital Wallet / UPI, Brokerage*), track custom starting balances, and automatically aggregate all funds into **one combined net financial balance**. When logging expenses, optionally specify which bank account paid for it to track deductions in real-time.
- 🔐 **Account Creation & 12-Word Mnemonic Backup**: Create private user accounts with decentralized 12-word backup recovery phrases (BIP-39 style). If you ever forget your password, your 12 keywords allow instant account recovery and password reset.
- 📱 **Mobile, Tablet & Desktop Web App**: Native app feel with a bottom navigation bar and floating `+` action button on mobile, adaptive 2-column cards on tablet, and a wide analytics sidebar dashboard on desktop.
- 💵 **Multi-Currency Support**: Instant 1-click currency switching across **10+ currencies** (`USD $`, `INR ₹`, `EUR €`, `GBP £`, `JPY ¥`, `CAD C$`, `AUD A$`, `AED`, `SGD S$`, `CHF`), updating charts, tables, budgets, and Excel exports dynamically.
- 📊 **Interactive Financial Analytics**: Chart.js graphs for category distribution (doughnut), daily spending trends (bar), 6-month historical comparison, and payment method share.
- 📑 **Executive Excel Integration**: Export formatted multi-tab `.xlsx` workbooks with live Excel formulas (`=SUM(...)`), currency formatting, zebra striping, auto-filters, and a dedicated **Bank Accounts & Combined Net Balance** sheet.
- 📥 **Spreadsheet Import & Template**: Bulk import expenses from Excel spreadsheets with automatic category mapping and validation.
- 🎯 **Category & Budget Management**: Track monthly budgets with visual progress meters and alert thresholds (*On Track*, *Near Limit >80%*, *Over Budget >100%*).
- 🌓 **Dark / Light Mode**: Instant theme switching with persistent state and chart palette synchronization.

---

## 📱 Multi-Device Responsive Design

| Platform | Features |
| :--- | :--- |
| **Desktop Web App** | Fixed left sidebar navigation, wide 4-card metric strip, side-by-side interactive charts, full-featured transactions table with live search and multi-criteria filters. |
| **Tablet Web App** | Touch-optimized 2-column layout, adaptive charts, comfortable tap targets, responsive category cards. |
| **Mobile Web App** | Native bottom navigation bar (*Home, Expenses, Quick Add (+), Reports, Budgets*), mobile card transactions, numeric keyboard optimization, and bottom-sheet expense modals. |

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3 (Flask)
- **Database**: SQLite3 (`expenses.db`) with relational integrity, foreign keys, and indexes
- **Spreadsheets / Reporting**: `openpyxl` (multi-sheet formatted `.xlsx` generation & parsing)
- **Frontend**: HTML5, Tailwind CSS, FontAwesome 6, Chart.js 4

---

## 🚀 Quick Start Guide

### 1. Clone the Repository
```bash
git clone https://github.com/Akhil-Binu/personal-expense-tracker.git
cd personal-expense-tracker
```

### 2. Set Up Python Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate on Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Or Windows Command Prompt:
.\.venv\Scripts\activate.bat
# Or macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
python run.py
```

The launcher will display your local and network access links and automatically open your default browser:
- **Desktop Web App**: `http://localhost:5000`
- **Mobile / Tablet (on same Wi-Fi)**: `http://<your-lan-ip>:5000` *(e.g. `http://192.168.1.50:5000`)*

---

## 📲 Accessing on Mobile & Tablet

1. Connect your smartphone or tablet to the **same Wi-Fi network** as your PC.
2. Launch `python run.py`.
3. Note the **Tablet / Mobile URL** printed in the terminal (e.g., `http://192.168.x.x:5000`).
4. Open Chrome or Safari on your phone and browse to that address.
5. *(Tip)* Tap **"Add to Home Screen"** in Safari / Chrome for a standalone full-screen web app experience!

---

## 📑 Excel Features

### 1. Executive Summary Export (.xlsx)
Generates a multi-sheet formatted workbook matching your selected month and currency:
- **Executive Summary Sheet**:
  - Branded header banner and KPI cards (*Total Spent, Monthly Budget, Remaining Buffer, Daily Average, Total Transactions, Top Category*).
  - Category Breakdown Table with live formulas (`=B9-C9`), budget utilization percentage, and currency formatting.
  - Payment Methods Overview section.
- **All Transactions Sheet**:
  - Filterable table with columns: ID, Date, Category, Description, Payment Method, Amount, Notes.
  - Auto-filter enabled on all headers.
  - Bottom Total Row with `=SUM(...)` formula.

### 2. Bulk Import from Excel
- Click **"Import"** or **"Import Excel"** to upload any `.xlsx` spreadsheet.
- Maps headers (`Date`, `Category`, `Amount`, `Payment Method`, `Description`, `Notes`).
- Auto-creates new categories if they don't already exist.
- Download a pre-formatted template with 1-click via the import dialog.

---

## 🪙 Supported Currencies

Switch between currencies anytime from the top navigation bar:
- 🇺🇸 **USD ($)** — US Dollar
- 🇮🇳 **INR (₹)** — Indian Rupee
- 🇪🇺 **EUR (€)** — Euro
- 🇬🇧 **GBP (£)** — British Pound
- 🇯🇵 **JPY (¥)** — Japanese Yen
- 🇨🇦 **CAD (C$)** — Canadian Dollar
- 🇦🇺 **AUD (A$)** — Australian Dollar
- 🇦🇪 **AED (AED)** — UAE Dirham
- 🇸🇬 **SGD (S$)** — Singapore Dollar
- 🇨🇭 **CHF (CHF)** — Swiss Franc

---

## 🧪 Automated Testing

FinanceFlow includes a comprehensive unit test suite covering routes, JSON APIs, SQLite CRUD operations, and Excel import/export:

```bash
.\.venv\Scripts\python.exe test_app.py
```

Output:
```
..........
----------------------------------------------------------------------
Ran 10 tests in 1.838s

OK
```

---

## 🔐 Account Creation & Backup Keywords System

FinanceFlow includes user authentication designed for privacy and resilience:

1. **Sign Up**:
   - Create your personal account with a unique username and password.
   - The app automatically creates a private sandbox for your expenses and budgets.

2. **12-Word Backup Keywords (Recovery Phrase)**:
   - When registering, FinanceFlow generates **12 cryptographically random, memorable dictionary words** (e.g., `acorn amber anchor beacon blossom clover...`).
   - You can copy them or download them as a `.txt` file.
   - The recovery phrase is securely hashed in SQLite using salted Werkzeug hashes.

3. **Account Recovery & Password Reset**:
   - If you ever forget your password, navigate to **Forgot Password?** (`/recover`).
   - Enter your username, type or paste your **12 backup keywords**, and set your new password.
   - Instant recovery with **zero external email dependencies**.

---

## 🏛️ Multi-Bank Account Management & Combined Net Balance

FinanceFlow includes comprehensive bank account tracking:
- **Multiple Bank Accounts**: Add checking, high-yield savings, digital wallets / UPI, or brokerage accounts with starting balances and masked account numbers.
- **Combined Net Balance**: View an aggregated real-time calculation of your total combined net balance in one consolidated hero view across all accounts.
- **Transaction Linking**: When recording or importing expenses, select the bank account to automatically deduct expenses from that specific account.
- **Aggregated Types Breakdown**: Filter and view combined balances grouped by account type (*Checking, Savings, Digital Wallets*).
- **Excel Export Inclusion**: Detailed bank account records and combined sums are exported in a dedicated sheet in the `.xlsx` export.

---

## 📁 Repository Structure

```
personal-expense-tracker/
├── app.py                # Flask server, authentication, page routes & REST endpoints
├── auth_service.py       # Password hashing & 12-word mnemonic recovery phrase generator
├── database.py           # SQLite connection, multi-user schema & transactional queries
├── excel_service.py      # openpyxl formatted workbook generator & parser
├── run.py                # Smart launcher with local LAN IP resolution
├── test_app.py           # Comprehensive unit tests (all 10 tests passing)
├── requirements.txt      # Frozen pip dependencies
├── .gitignore            # Git exclusion rules
├── LICENSE               # MIT License
├── static/
│   ├── css/
│   │   └── style.css     # Responsive styles, mobile touch rules, toast animations
│   └── js/
│       └── app.js        # Theme manager, Chart.js renderers, modals, currency API, accounts
└── templates/
    ├── base.html         # Responsive base layout (Desktop sidebar + Mobile bottom nav)
    ├── login.html        # Clean login interface with recovery link
    ├── register.html     # Account creation interface
    ├── backup_keywords.html # 12-word mnemonic keywords presentation card
    ├── recover.html      # Account recovery & password reset using 12 keywords
    ├── index.html        # Main dashboard (Combined Balance banner, KPI cards, charts)
    ├── accounts.html     # Bank Accounts & Combined Net Balance management view
    ├── expenses.html     # Expenses table, advanced filters, search & Excel export
    ├── reports.html      # Monthly reports, 4 interactive charts, variance table
    └── categories.html   # Category budgets, limits & progress bars
```

---

## 📄 License

This project is open-source under the [MIT License](LICENSE).
