import sqlite3
from datetime import datetime, timezone
import random
import string

DB_PATH = "tickets.db"


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create the tickets table
cursor.execute('''
CREATE TABLE IF NOT EXISTS tickets (
    ticket_name TEXT PRIMARY KEY,
    status TEXT,
    subject TEXT,
    user_email TEXT,
    thread_id_user TEXT,
    thread_id_admin TEXT,
    created_at TEXT
)
''')

# Create separate tables for each type of history
cursor.execute('''
CREATE TABLE IF NOT EXISTS history_user (
    ticket_name TEXT,
    role TEXT,
    message TEXT,
    timestamp TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS history_admin (
    ticket_name TEXT,
    role TEXT,
    message TEXT,
    timestamp TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS email_history (
    ticket_name TEXT,
    role TEXT,
    message TEXT,
    timestamp TEXT
)
''')

conn.commit()


def clean_history(history):
    return '\n'.join([f'{entry[0].title()}: {entry[1]}' for entry in history])


class DatabaseHandler:
    def __init__(self, db_path=DB_PATH):
        self.conn = self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.conn.close()

    def generate_ticket(self, user_email, temp_history):
        ticket_name = None
        characters = string.ascii_uppercase + string.digits
        while not ticket_name or ticket_name in self.get_all_ticket_names():
            ticket_name = random.choice(string.ascii_uppercase) + ''.join(random.choices(characters, k=6))

        created_at = datetime.now(timezone.utc).isoformat()
        self.cursor.execute('''
            INSERT OR REPLACE INTO tickets (ticket_name, status, subject, user_email, \
            thread_id_user, thread_id_admin, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (ticket_name, 'open', None, user_email, None, None, created_at))
        self.conn.commit()

        for entry in temp_history:
            role = entry["role"]
            message = entry["message"]
            self.append_history("history_user", ticket_name, role, message)

        temp_history.clear()

        return ticket_name

    def update_ticket_field(self, ticket_name, field, value):
        self.cursor.execute(f'''
            UPDATE tickets SET {field} = ? WHERE ticket_name = ?
        ''', (value, ticket_name))
        self.conn.commit()

    def get_ticket_field(self, ticket_name, field):
        self.cursor.execute(f'SELECT {field} FROM tickets WHERE ticket_name = ?', (ticket_name,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_ticket(self, ticket_name):
        self.cursor.execute('SELECT status, subject, user_email, thread_id_user, thread_id_admin, '
                            'created_at FROM tickets WHERE ticket_name = ?', (ticket_name,))
        result = self.cursor.fetchone()
        return result if result else None

    def get_all_ticket_names(self):
        query = 'SELECT ticket_name FROM tickets ORDER BY created_at DESC'
        self.cursor.execute(query)
        return [row[0] for row in self.cursor.fetchall()]

    def append_history(self, table, ticket_name, role, message):
        timestamp = datetime.now(timezone.utc).isoformat()
        self.cursor.execute(f'''
            INSERT INTO {table} (ticket_name, role, message, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (ticket_name, role, message, timestamp))
        self.conn.commit()

    def get_history(self, table, ticket_name, select='role, message'):
        self.cursor.execute(f'SELECT {select} FROM {table} WHERE ticket_name = ?', (ticket_name,))
        return self.cursor.fetchall()

    def close_ticket(self, ticket_name):
        self.update_ticket_field(ticket_name, 'status', 'closed')

    def tickets_as_dict(self):
        tickets_dict = {}

        for ticket_name in self.get_all_ticket_names():
            status, subject, user_email, thread_id_user, thread_id_admin, created_at = self.get_ticket(ticket_name)
            user_history = self.get_history('history_user', ticket_name)
            dicted_user_history = [{'role': entry[0], 'message': entry[1]} for entry in user_history]
            admin_history = self.get_history('history_admin', ticket_name)
            dicted_admin_history = [{'role': entry[0], 'message': entry[1]} for entry in admin_history]

            tickets_dict[ticket_name] = {
                'status': status,
                'subject': subject,
                'user_email': user_email,
                'history_user': dicted_user_history,
                'history_admin': dicted_admin_history,
                'threadIds': [thread_id_user, thread_id_admin],
                'created_at': created_at
            }

        return tickets_dict
