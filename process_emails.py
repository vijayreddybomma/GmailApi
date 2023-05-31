import os
import json
import re
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Path to credentials.json file
CREDENTIALS_PATH = "credentials.json"

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


# Path to rules.json file
RULES_PATH = "rules.json"


def main():
    # Authenticate with Gmail API using OAuth
    credentials = get_credentials()
    service = build("gmail", "v1", credentials=credentials)

    # Fetch emails from Gmail API
    emails = fetch_emails_from_api(service)

    # Load rules from rules.json file
    rules = load_rules_from_file()

    # Process emails based on rules and take actions
    process_emails(emails, rules, service)


def get_credentials():
    # Load credentials from credentials.json file
    credentials = None
    if os.path.exists(CREDENTIALS_PATH):
        with open(CREDENTIALS_PATH, "r") as f:
            credentials_data = json.load(f)
            credentials = Credentials.from_authorized_user_info(
                credentials_data, SCOPES
            )
    else:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
        credentials = flow.run_local_server(port=0)
        save_credentials(credentials)

    return credentials


def save_credentials(credentials):
    # Save credentials to credentials.json file
    credentials_data = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(credentials_data, f)


def fetch_emails_from_api(service):
    # Fetch emails from Gmail API
    response = (
        service.users().messages().list(userId="me", labelIds=["INBOX"]).execute()
    )
    messages = response.get("messages", [])

    emails = []
    for message in messages:
        email = service.users().messages().get(userId="me", id=message["id"]).execute()
        emails.append(email)

    return emails


def load_rules_from_file():
    # Load rules from rules.json file
    with open(RULES_PATH) as file:
        rules = json.load(file)
    return rules


def process_emails(emails, rules, service):
    for email in emails:
        # Extract email information
        subject = get_email_header(email, "Subject")
        sender = get_email_header(email, "From")
        received_date = get_email_received_date(email)

        # Apply rules and take actions
        for rule in rules:
            conditions = rule["conditions"]
            actions = rule["actions"]

            # Check if all conditions are satisfied
            if all(check_condition(email, condition) for condition in conditions):
                # Perform actions on the email
                for action in actions:
                    perform_action(service, email, action)


def get_email_header(email, header_name):
    # Get the value of a header field from the email
    headers = email["payload"]["headers"]
    for header in headers:
        if header["name"] == header_name:
            return header["value"]
    return ""


def get_email_received_date(email):
    # Get the received date of the email
    received_header = get_email_header(email, "Received")
    match = re.search(r"(\d{1,2} [A-Za-z]{3} \d{4} \d{2}:\d{2}:\d{2})", received_header)
    if match:
        received_date_str = match.group(1)
        return received_date_str
    return ""


def check_condition(email, condition):
    field_name = condition["fieldName"]
    predicate = condition["predicate"]
    value = condition["value"]

    if field_name == "Received Date":
        return apply_date_predicate(get_email_received_date(email), predicate, value)
    else:
        # Handle other field conditions
        pass


def apply_string_predicate(value, predicate, condition):
    # Apply string predicate on the value
    if predicate == "Contains":
        return condition.lower() in value.lower()
    elif predicate == "Does not Contain":
        return condition.lower() not in value.lower()
    elif predicate == "Equals":
        return value.lower() == condition.lower()
    elif predicate == "Does not equal":
        return value.lower() != condition.lower()
    return False


def apply_date_predicate(received_date, predicate, value):
    condition_date = datetime.now().date() - timedelta(days=int(value))
    received_date = datetime.strptime(received_date, "%d %b %Y").date()

    if predicate == "Less than":
        return received_date < condition_date
    elif predicate == "Greater than":
        return received_date > condition_date
    elif predicate == "Equals":
        return received_date == condition_date

    return False


def perform_action(service, email, action):
    # Perform an action on the email
    if action == "Mark as read":
        mark_email_as_read(service, email)
    elif action == "Mark as unread":
        mark_email_as_unread(service, email)
    elif action == "Move to inbox":
        move_email_to_inbox(service, email)


def mark_email_as_read(service, email):
    # Mark the email as read
    message_id = email["id"]
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
    ).execute()


def mark_email_as_unread(service, email):
    # Mark the email as unread
    message_id = email["id"]
    service.users().messages().modify(
        userId="me", id=message_id, body={"addLabelIds": ["UNREAD"]}
    ).execute()


def move_email_to_inbox(service, email):
    # Move the email to the inbox
    message_id = email["id"]
    service.users().messages().modify(
        userId="me", id=message_id, body={"removeLabelIds": ["INBOX"]}
    ).execute()


if __name__ == "__main__":
    main()
