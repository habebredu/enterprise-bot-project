import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from email.message import EmailMessage
from email import message_from_bytes
from email.utils import parseaddr
import base64

import vector
from chatbot import generate_subject, summarise_solution
from ticket_manager import DatabaseHandler, clean_history

import time
import json

SCOPES = ["https://mail.google.com/"]

ADMIN = "habeb.rizmi@hotmail.com"
CHATBOT = "habeb.chat.bot@gmail.com"

def get_service():
    token_data = os.getenv("GOOGLE_TOKEN_JSON")

    if not token_data:
        raise RuntimeError("Missing GOOGLE_TOKEN_JSON in environment.")

    creds = Credentials.from_authorized_user_info(json.loads(token_data), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())

    return build("gmail", "v1", credentials=creds)
    

def get_or_create_label(label_name):
    service = get_service()

    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']
    label_body = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    label = service.users().labels().create(userId='me', body=label_body).execute()
    return label['id']


def send_email(to, ticket_name):
    print("Email requested...")
    service = get_service()
    db2 = DatabaseHandler()

    if db2.get_ticket_field(ticket_name, 'status') == 'closed':
        return

    ticketed_label_id = get_or_create_label('TICKETED')
    child_label_id = get_or_create_label(f'TICKETED/{ticket_name}')

    if to == ADMIN:
        if not db2.get_history('email_history', ticket_name):
            msg = (clean_history(db2.get_history('history_user', ticket_name)))
        else:
            msg = clean_history([db2.get_history('history_user', ticket_name)[-1]])  # List input expected here

        subject = f'New Message from {ticket_name}'

        message = EmailMessage()
        message.set_content(msg)
        message["To"] = to
        message["From"] = CHATBOT
        message["Subject"] = subject

        print(db2.get_history('history_admin', ticket_name))
        if db2.get_history('history_admin', ticket_name):  # Is previous bot-admin conversation present?
            thread_id = db2.get_ticket_field(ticket_name, 'thread_id_admin')
            thread = (service
                      .users()
                      .threads()
                      .get(userId='me', id=thread_id)
                      .execute())

            latest_message = thread['messages'][-1]
            headers = latest_message["payload"]["headers"]
            in_reply_to = next(h["value"] for h in headers if h["name"].lower() == "message-id")
            message["In-Reply-To"] = in_reply_to  # Reply to latest message in thread rather than sending a new email
            message["References"] = in_reply_to

        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        try:
            sent_msg = service.users().messages().send(userId="me", body=create_message).execute()
        except Exception as e:
            logger.info(e)
        msg_id = sent_msg['id']
        thread_id = sent_msg['threadId']
        db2.update_ticket_field(ticket_name, 'thread_id_admin', thread_id)

        if not db2.get_history('history_admin', ticket_name):  # If first message in the thread
            service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={
                    'addLabelIds': [ticketed_label_id, child_label_id]
                }
            ).execute()

        else:
            db2.append_history('history_admin', ticket_name, 'bot', msg)

    else:
        msg = db2.get_history('history_admin', ticket_name, select='message')[-1][0]  # (message,)

        message = EmailMessage()
        message.set_content(msg)
        message["To"] = to
        message["From"] = CHATBOT

        if not db2.get_history('email_history', ticket_name):  # If no previous bot-user email conversation
            subject_main = generate_subject(clean_history(db2.get_history('history_user', ticket_name)))
            subject = f"{subject_main} | Ticket {ticket_name}"
            message["Subject"] = subject
            db2.update_ticket_field(ticket_name, 'subject', subject)

        else:
            message["Subject"] = db2.get_ticket_field(ticket_name, 'subject')

            thread_id = db2.get_ticket_field(ticket_name, 'thread_id_user')
            thread = (service
                      .users()
                      .threads()
                      .get(userId='me', id=thread_id)
                      .execute())

            latest_message = thread['messages'][-1]
            headers = latest_message["payload"]["headers"]
            in_reply_to = next(h["value"] for h in headers if h["name"].lower() == "message-id")
            message["In-Reply-To"] = in_reply_to  # Reply to latest message in thread rather than sending a new email
            message["References"] = in_reply_to

        create_message = {"raw": base64.urlsafe_b64encode(message.as_bytes()).decode()}
        sent_msg = service.users().messages().send(userId="me", body=create_message).execute()
        msg_id = sent_msg['id']
        thread_id = sent_msg['threadId']
        db2.update_ticket_field(ticket_name, 'thread_id_user', thread_id)

        if not db2.get_ticket_field(ticket_name, 'subject'):  # Only need to label the first message in the thread
            service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={
                    'addLabelIds': [ticketed_label_id, child_label_id]
                }
            ).execute()

        else:
            db2.append_history('email_history', ticket_name, 'bot', msg)


def extract_message(msg_id):
    service = get_service()
    msg = service.users().messages().get(userId='me', id=msg_id, format='raw').execute()
    raw_data = base64.urlsafe_b64decode(msg['raw'].encode('ASCII'))
    email_message = message_from_bytes(raw_data)

    service.users().messages().modify(
        userId='me',
        id=msg_id,
        body={
            'removeLabelIds': ['UNREAD']
        }
    ).execute()

    print("Email marked as read")

    # Get the plain text body
    body = ""
    if email_message.is_multipart():
        for part in email_message.walk():
            if part.get_content_type() == 'text/plain':
                body = part.get_payload(decode=True).decode("windows-1252")
                break
    else:
        body = email_message.get_payload(decode=True).decode("windows-1252")

    return parseaddr(email_message['From'])[1].lower(), email_message['Subject'], body


def background_ticket_watcher():
    service = get_service()
    db = DatabaseHandler()

    while True:
        for ticket_name in db.get_all_ticket_names():
            if db.get_ticket_field(ticket_name, 'status') == 'closed':
                continue

            # Loop through bot-user thread ID, then bot-admin thread ID
            for thread_id in [db.get_ticket_field(ticket_name, 'thread_id_user'),
                              db.get_ticket_field(ticket_name, 'thread_id_admin')]:
                if not thread_id:  # Thread not initialised yet, i.e. no message sent yet
                    continue

                thread = (service
                          .users()
                          .threads()
                          .get(userId='me', id=thread_id)
                          .execute())
                messages = thread['messages']

                # Check for unread replies in thread
                for msg in messages:
                    if 'UNREAD' in msg['labelIds']:
                        from_addr, subject, body = extract_message(msg['id'])
                        if from_addr == ADMIN:
                            to = db.get_ticket_field(ticket_name, 'user_email')
                            db.append_history('history_admin', ticket_name, 'admin', body)
                            db.append_history('email_history', ticket_name, 'bot', body)
                        else:
                            to = ADMIN
                            db.append_history('email_history', ticket_name, 'user', body)
                        send_email(to, ticket_name)

                        # TODO: Add an interactive way on the website to close a ticket, for now using a code phrase
                        if "I will be closing this ticket now" in body:
                            db.close_ticket(ticket_name)
                            solution_summary = summarise_solution(ticket_name)
                            vector.add_documents([solution_summary])

        time.sleep(15)
