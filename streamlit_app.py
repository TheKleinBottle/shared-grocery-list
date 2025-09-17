import streamlit as st
import sqlite3
from collections import defaultdict

DB_FILE = "expenses.db"

# ------------------ DATABASE ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS participants (name TEXT PRIMARY KEY)""")
    c.execute("""CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY, payer TEXT, amount REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS repayments (id INTEGER PRIMARY KEY, payer TEXT, payee TEXT, amount REAL)""")
    conn.commit()
    conn.close()

def add_participant(name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO participants VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_participants():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT name FROM participants")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows

def add_transaction(payer, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO transactions (payer, amount) VALUES (?, ?)", (payer, amount))
    conn.commit()
    conn.close()

def add_repayment(payer, payee, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO repayments (payer, payee, amount) VALUES (?, ?, ?)", (payer, payee, amount))
    conn.commit()
    conn.close()

def get_transactions():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT payer, amount FROM transactions")
    rows = c.fetchall()
    conn.close()
    return rows

def get_repayments():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT payer, payee, amount FROM repayments")
    rows = c.fetchall()
    conn.close()
    return rows

# ------------------ LOGIC ------------------
def compute_matrix(participants, transactions, repayments):
    n = len(participants)
    paid = defaultdict(float)
    for payer, amount in transactions:
        paid[payer] += amount

    total = sum(paid.values())
    share = total / n if n > 0 else 0
    balances = {p: paid[p] - share for p in participants}

    # Build matrix
    matrix = {p: {q: 0.0 for q in participants} for p in participants}
    for creditor in participants:
        if balances[creditor] > 0:
            for debtor in participants:
                if balances[debtor] < 0 and creditor != debtor:
                    amt = min(balances[creditor], -balances[debtor])
                    matrix[debtor][creditor] += amt
                    balances[creditor] -= amt
                    balances[debtor] += amt

    # Subtract repayments
    for payer, payee, amount in repayments:
        matrix[payer][payee] -= amount
        if matrix[payer][payee] < 0:
            matrix[payer][payee] = 0

    return matrix

def compute_net(matrix, participants):
    net = {p: 0 for p in participants}
    for debtor in participants:
        for creditor in participants:
            net[creditor] += matrix[debtor][creditor]
            net[debtor] -= matrix[debtor][creditor]
    return net

# ------------------ STREAMLIT UI ------------------
init_db()
st.title("💸 Shared Expense Tracker")

# Add participants
st.sidebar.header("Add Participants")
new_name = st.sidebar.text_input("Name")
if st.sidebar.button("Add"):
    if new_name.strip():
        add_participant(new_name.strip())

participants = get_participants()
if not participants:
    st.warning("⚠️ Add participants from the sidebar to get started!")

# Add expense
st.header("➕ Add Expense")
payer = st.selectbox("Who paid?", participants)
amount = st.number_input("Amount", min_value=0.0, step=10.0)
if st.button("Add Expense"):
    add_transaction(payer, amount)
    st.success(f"Added {payer} spent {amount}")

# Add repayment
st.header("🔁 Add Repayment")
from_person = st.selectbox("From", participants)
to_person = st.selectbox("To", [p for p in participants if p != from_person])
rep_amt = st.number_input("Repayment Amount", min_value=0.0, step=10.0, key="rep")
if st.button("Add Repayment"):
    add_repayment(from_person, to_person, rep_amt)
    st.success(f"Added repayment {from_person} → {to_person}: {rep_amt}")

# Display matrix + balances
transactions = get_transactions()
repayments = get_repayments()
matrix = compute_matrix(participants, transactions, repayments)
net = compute_net(matrix, participants)

st.subheader("📊 Owes Matrix")
st.write(matrix)

st.subheader("💰 Net Balances")
st.write(net)

st.subheader("🧾 All Transactions")
st.write(transactions)

st.subheader("📉 All Repayments")
st.write(repayments)
