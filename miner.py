import re
import csv
from datetime import datetime
import argparse
import os

timezoneOffset = 3  # Default timezone offset for Finland (UTC+3)

def parse_log_file(log_file_path, output_csv_path):
    """
    Parses the log file to track student session details and writes the data to a CSV file.

    Args:
        log_file_path (str): Path to the log file.
        output_csv_path (str): Path to the output CSV file.
    """
    session_start_pattern = re.compile(
        r'^\w{3} \d{2} \d{2}:\d{2}:\d{2} \d+\.\d+\.\d+\.\d+ ktpjs\[\d+\]:  '
        r'{"level":"info","message":"(?P<ip>[\d\.]+) session authorized: '
        r'(?P<session_id>[a-f0-9\-]+) student: (?P<student_id>[a-f0-9\-]+) '
        r'\\"(?P<student_name>[^\\]+)\\" exam: (?P<exam_id>[a-f0-9\-]+)"}'
    )
    activity_pattern = re.compile(
        r'^\w{3} \d{2} \d{2}:\d{2}:\d{2} \d+\.\d+\.\d+\.\d+ ktpjs\[\d+\]:  '
        r'{"level":"info","message":"student (?P<student_id>[a-f0-9\-]+) '
        r'answered to question (?P<question_id>\d+) with \d+ characters.*"}'
    )
    session_end_pattern = re.compile(
        r'^\w{3} \d{2} \d{2}:\d{2}:\d{2} \d+\.\d+\.\d+\.\d+ ktpjs\[\d+\]:  '
        r'{"level":"info","message":"Student (?P<student_id>[a-f0-9\-]+) '
        r'ending session"}'
    )
    activity_logged_pattern = re.compile(
        r'^\w{3} \d{2} \d{2}:\d{2}:\d{2} \d+\.\d+\.\d+\.\d+ ktpjs\[\d+\]:  '
        r'{"level":"info","message":"Student (?P<student_id>[a-f0-9\-]+) '
        r'activity logged: Examining answers \(EXAMINE_EXAM\)"}'
    )
    counter = 0
    sessions = dict()
    with open(log_file_path, 'r', encoding='utf-8') as log_file:
        for line in log_file:
            counter += 1
            line = line.strip()
            # Match session start
            start_match = session_start_pattern.match(line)
            if start_match:
                student_id = start_match.group("student_id")
                exam_id = start_match.group("exam_id")
                student_name = start_match.group("student_name")
                timestamp = extract_timestamp(line, timezone_offset=timezoneOffset)
                sessions[student_id] = {
                    "student_name": student_name,
                    "exam_id": exam_id,
                    "student_id": student_id,
                    "nr_of_answers": 0,
                    "nr_of_questions": 0,
                    "tmp_questions": dict(),
                    "start_time": timestamp,
                    "end_time": None,
                    "last_activity_time": None,
                }
                continue

            # Match activity
            activity_match = activity_pattern.match(line)
            if activity_match:
                # check if the student_id is in sessions
                student_id = activity_match.group("student_id")
                if student_id in sessions:
                    sessions[student_id]["nr_of_answers"] += 1
                    sessions[student_id]["tmp_questions"][int(activity_match.group("question_id"))] = 1
                    sessions[student_id]["nr_of_questions"] = len(sessions[student_id]["tmp_questions"])
                    sessions[student_id]["last_activity_time"] = extract_timestamp(line, timezone_offset=timezoneOffset)
                continue

            # Match activity logged
            activity_logged_match = activity_logged_pattern.match(line)
            if activity_logged_match:
                student_id = activity_logged_match.group("student_id")
                if student_id in sessions:
                    sessions[student_id]["end_time"] = extract_timestamp(line, timezone_offset=timezoneOffset)
                continue

            # Match session end
            end_match = session_end_pattern.match(line)
            if end_match:
                student_id = end_match.group("student_id")
                if student_id in sessions:
                    sessions[student_id]["end_time"] = extract_timestamp(line, timezone_offset=timezoneOffset)

    print(f"Parsed {len(sessions)} sessions from the log file with {counter} lines.")
    # Write to CSV
    # Ensure the directory for the output CSV file exists
    os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)

    # remove the tmp_questions key from each session
    for session in sessions.values():
        session.pop("tmp_questions", None)
    # Write the sessions to the CSV file

    with open(output_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=[
            "student_name", "student_id", "exam_id", "start_time", "last_activity_time", "end_time", "nr_of_answers", "nr_of_questions"
        ])
        writer.writeheader()
        for session in sessions.values():
            writer.writerow(session)

def extract_timestamp(log_line, timezone_offset=3):
    """
    Extracts the timestamp from a log line.

    Args:
        log_line (str): A single line from the log file.

    Returns:
        str: The extracted timestamp in ISO format.
    """
    timestamp_str = log_line[:15]  # Extract the first 15 characters (e.g., "Apr 28 11:57:32")
    timestamp = datetime.strptime(timestamp_str, "%b %d %H:%M:%S")
    # Adjust the timezone offset
    if timezone_offset != 0:
        hours = int(timezone_offset)
        timestamp = timestamp.replace(hour=(timestamp.hour + hours) % 24)
    # Add the current year to the timestamp
    timestamp = timestamp.replace(year=datetime.now().year)
    return timestamp.isoformat()

def __main__():
    parser = argparse.ArgumentParser(description='Parse Abitti log file and generate CSV report')
    parser.add_argument('--log', type=str, help='Path to the log file', required=True)
    parser.add_argument('--csv', type=str, help='Path to the output CSV file', required=True)
    parser.add_argument('--timezoneOffset', type=int, help='Timezone deviation', default='+3')
    args = parser.parse_args()
    # Set timezone offset based on the argument
    timezoneOffset = int(args.timezoneOffset)
    log_file_path = args.log
    output_csv_path = args.csv
    parse_log_file(log_file_path, output_csv_path)



if __name__ == "__main__":
    __main__()