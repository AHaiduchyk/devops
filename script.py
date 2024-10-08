import os
import base64
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import pytz
import re
from datetime import datetime
import json

import logging
logging.basicConfig(filename='myapp.log', level=logging.INFO)
logger = logging.getLogger(__name__)


def load_state():
    state = {}
    if os.path.exists('state.json'):
        with open('state.json', 'r') as state_file:
            state = json.load(state_file)
    return state

def save_state(state):
    with open('state.json', 'w') as state_file:
        json.dump(state, state_file)
    return state
        
def get_state():
    state = load_state()
    if 'last_run_timestamp' in state:
        return int(str(state['last_run_timestamp'])+'000')
    else:
        # If state file doesn't contain last run timestamp, return 0
        return 0
    
# Define your scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/spreadsheets']




def extract_information_from_message(message):
    # Regular expressions for extracting job title, city, name, contact information, application URL, and age
    job_title_pattern = r'вакансію\s*(.*?),\s*[^,]+,'
    city_pattern_1 = r'Місто:\s(.*?)\n'
    city_pattern_2 = r'Місто проживання:\s(.*?)\n'
    name_pattern = r'Резюме від \d+ \w+ (\d+)\n(.*?)\n'
    phone_pattern=r'Телефон:\s(.*?)\n'
    mail_pattern=r'пошта:\s(.*?)\n'
    url_pattern = r'Перейти у «Відгуки» (https?://\S+)'
    age_pattern = r'Вік:\s(\d+)\s'

    # Extracting job title, city, name, contact information, application URL, and age
    job_title = re.search(job_title_pattern, message)
    
    # re.findall(r'вакансію(.*?),\s*\w+,', message)[0]
    try:
        city = re.findall(city_pattern_1, message)[0]
    except:
        try:
            city = re.findall(city_pattern_2, message)[0]
        except:
            city = ' '
        
    name = re.search(name_pattern, message)
    phone_number = re.search(phone_pattern, message)
    email = re.search(mail_pattern, message)
    application_url = re.search(url_pattern, message)
    age = re.search(age_pattern, message)
    
    job_title_val = job_title.group(1) if job_title else ' '
        
    city_val=city
              
    name_val = re.search(name_pattern, message).group(2) if name else ' '
    phone_val = re.search(phone_pattern, message).group(1) if phone_number else ' '
    email_val = re.search(mail_pattern, message).group(1) if email else ' '
    application_url_val = re.search(url_pattern, message).group(1) if application_url else ' '
    age_val = re.search(age_pattern, message).group(1) if age else ' '
    

    result={
        "Job Title": job_title_val.strip(),
        "City": city_val,
        "Name": name_val,
        "Phone Number": phone_val,
        "Email": email_val,
        "Application URL": application_url_val,
        "Age": age_val
    }

    return result
    
def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def fetch_emails(service, query):
    result = service.users().messages().list(userId='me', q=query).execute()
    messages = result.get('messages', [])
    return messages

def convert_timestamp_to_kyiv_time(timestamp_ms):
    """
    Convert a Unix timestamp in milliseconds to a datetime object in the Kyiv timezone.

    :param timestamp_ms: Unix timestamp in milliseconds
    :return: Datetime object in the Kyiv timezone
    """
    # Convert milliseconds to seconds
    timestamp_s = timestamp_ms / 1000.0
    
    # Convert to UTC datetime object
    utc_datetime = datetime.utcfromtimestamp(timestamp_s)
    
    # Define Kyiv timezone
    kyiv_tz = pytz.timezone('Europe/Kyiv')
    
    # Convert UTC datetime to Kyiv timezone
    kyiv_datetime = utc_datetime.replace(tzinfo=pytz.utc).astimezone(kyiv_tz)
    
    return kyiv_datetime


def parse_email(message, service, state_timestamp_var):
    msg = service.users().messages().get(userId='me', id=message['id']).execute()
    # Convert internalDate to timestamp
    receiving_time = int(msg['internalDate'])
    
    if receiving_time > state_timestamp_var:
        logger.info(f'State: {state_timestamp_var}, receiving_time:, {receiving_time}')
        print(f'State: {state_timestamp_var}, receiving_time:, {receiving_time}')
        # Process the email only if it was received after the last script run
        payload = msg['payload']
        headers = payload['headers']
        subject = [header['value'] for header in headers if header['name'] == 'Subject'][0]
        encoded_data = find_key_occurrences(msg, 'data')[0][1]
        decoded_data = base64.urlsafe_b64decode(encoded_data).decode('utf-8')

        res = extract_information_from_message(decoded_data)
        msg_datetime = convert_timestamp_to_kyiv_time(receiving_time)
        res['Date'] = msg_datetime.strftime('%d.%m.%Y')

        # Define the desired order and new keys/values to add
        correct_order = ['Date', 'Name', 'Age', 'City', 'Phone Number', 'Email', 'Empty_field', 'Status', 'Application URL', 'Source', 'Job Title']
        new_keys = {'Empty_field': ' ', 'Status': 'hot', 'Source': 'WORK UA'}

        # Create a new dictionary with desired order and new keys/values
        reordered_dict = {key: res.get(key, new_keys.get(key, '')) for key in correct_order}

        return reordered_dict
    else:
        # Email received before the last script run, ignore it
        return None

def find_key_occurrences(data, target_key, path=''):
    occurrences = []

    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            if key == target_key:
                occurrences.append((current_path, value))
            occurrences.extend(find_key_occurrences(value, target_key, current_path))

    elif isinstance(data, list):
        for index, item in enumerate(data):
            current_path = f"{path}[{index}]"
            occurrences.extend(find_key_occurrences(item, target_key, current_path))

    return occurrences
  
def write_to_sheet(service, spreadsheet_id, data):
    logger.info(len(data))
    if not data:
        print("No data provided to append.")
        return "No data provided to append."

    for row_dict in data:
        # Extract the Job Title to determine the sheet name
        job_title = row_dict.pop('Job Title', 'Sheet1')

        # Prepare data for insertion, excluding the Job Title
        row = [str(value) for value in row_dict.values()]

        # Prepare the request body
        body = {
            'values': [row]
        }

        # Find the last row with data in the sheet
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{job_title}!A:A"  # Assuming column A always has data
        ).execute()
        last_row = len(result.get('values', [])) + 1  # Add 1 for the next row

        # Append new data to the end of the table
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{job_title}!A{last_row}",  # Append below the last row
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()

        print(f"Data has been appended to the {job_title} sheet in the Google Spreadsheet.")
    
    return "Data has been appended "


def main():
    
    state_timestamp_var = get_state()
    logger.info(f'{state_timestamp_var}')
    creds = authenticate_google()
    gmail_service = build('gmail', 'v1', credentials=creds)
    sheets_service = build('sheets', 'v4', credentials=creds)
    pattern = '{Кандидат з сайту Work.ua}{Відповісти}'

    # Fetch emails with specific query
    emails = fetch_emails(gmail_service, pattern)
    spreadsheet_id = '**************'

    data = []

    for email in emails:
        parsed_data = parse_email(email, gmail_service, state_timestamp_var)
        if parsed_data:
            data.append(parsed_data)

    data.sort(key=lambda x: x['Date'])

    # Update the state with the current timestamp
    last_run_timestamp=str(int(datetime.now().timestamp()))
    state = {'last_run_timestamp': last_run_timestamp}
    saved_state=save_state(state)
    logger.info(f'saved_state: {saved_state}')
    
    check_state=get_state()
    
    logger.info(f'check_state: {check_state}')
    
    kyiv_time=convert_timestamp_to_kyiv_time(float(last_run_timestamp+'000'))
    kyiv_time_str=kyiv_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Write data to Google Sheets
    result = write_to_sheet(sheets_service, spreadsheet_id, data)
    logger.info('Last run time:')
    logger.info(kyiv_time_str)
    del data
    del gmail_service
    del sheets_service
    
    return [result, kyiv_time_str]

# if __name__ == '__main__':
#     main()
    

