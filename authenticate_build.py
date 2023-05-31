import os
import json
from datetime import datetime
import re
import mysql.connector
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Path to credentials.json file
CREDENTIALS_PATH = "credentials.json"

# MySQL database configuration
MYSQL_HOST = "localhost"
MYSQL_USER = "vijay"
MYSQL_PASSWORD = "HelloWorld123#"
MYSQL_DATABASE = "happyfox"

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Rule-based operations configuration
RULES_PATH = "rules.json"


def main():
    # Authenticate with GMail API using OAuth
    credentials = get_credentials()
    service = build("gmail", "v1", credentials=credentials)

    # Fetch emails from GMail API
    emails = fetch_emails_from_api(service)

    # Store emails in MySQL database
    store_emails_in_database(emails)


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
        emails.append(parse_email(email))

    return emails


def parse_email(email):
    # Parse relevant information from email object
    headers = email["payload"]["headers"]
    subject = get_header_value(headers, "Subject")
    sender = get_header_value(headers, "From")
    received_datetime = get_received_datetime(email)

    return {
        "subject": subject,
        "sender": sender,
        "received_datetime": received_datetime,
    }


def get_header_value(headers, name):
    # Get value of a header field from email headers
    for header in headers:
        if header["name"] == name:
            return header["value"]
    return ""


def get_received_datetime(email):
    received_header = email["payload"]["headers"]
    received_datetime_str = None

    for header in received_header:
        if header["name"].lower() == "received":
            match = re.search(
                r"([a-zA-Z]{3}, \d{2} [a-zA-Z]{3} \d{4} \d{2}:\d{2}:\d{2} .\d{4})",
                header["value"],
            )
            if match:
                received_datetime_str = match.group(1)
                break

    if received_datetime_str:
        received_datetime = datetime.strptime(
            received_datetime_str, "%a, %d %b %Y %H:%M:%S %z"
        )
        return received_datetime.strftime("%Y-%m-%d")
    else:
        return None


def store_emails_in_database(emails):
    # Connect to the MySQL database
    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
    )
    cursor = conn.cursor()

    # Create the emails table if it doesn't exist
    create_emails_table(cursor)

    # Insert emails into the database
    for email in emails:
        insert_email(cursor, email)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()


def create_emails_table(cursor):
    # Create the emails table in MySQL if it doesn't exist
    create_table_query = """
        CREATE TABLE IF NOT EXISTS emails (
            id INT AUTO_INCREMENT PRIMARY KEY,
            subject VARCHAR(255),
            sender VARCHAR(255),
            received_datetime DATE
        )
    """
    cursor.execute(create_table_query)


def insert_email(cursor, email):
    # Insert an email into the emails table in MySQL
    insert_query = """
        INSERT INTO emails (subject, sender, received_datetime)
        VALUES (%s, %s, %s)
    """
    cursor.execute(
        insert_query,
        (email["subject"], email["sender"], email["received_datetime"]),
    )


if __name__ == "__main__":
    main()
