import requests
import os
import time
import smtplib
import csv

SERVER = 'mail.dhr-rgv.com'
PORT = 25
TO = 'b.serna@dhrhealth.com'
FROM = 'RepeatCallersAlert@dhrhealth.com'
target_url = "http://10.200.23.16:13798/process"
file_path = "" 
DIRECTORY = "C:/S/REPORTS"

def check_for_files():
    os.chdir(DIRECTORY)
    files = os.listdir(DIRECTORY)
    for filename in files:
        if 'CALLS' in filename:
            global file_path
            file_path = filename
            print("Call details report detected.")
            return True
        #if 'REPEAT' in filename:
         ##  print("Repeat callers report detected.")
           # check_for_repeats(file_path)

def check_for_repeats(file_path):
    file_path
    phone_numbers = []
    with open(file_path, 'r') as input:
        reader = csv.DictReader(input)
        phone_numbers = [[row['Phone Number'], row['Queue Name'].strip("*")] for row in reader]
        
        repeat_callers = {}
        for i in range(0, len(phone_numbers)):
            if phone_numbers.count(phone_numbers[i]) >= 3:
                if phone_numbers[i][0] not in repeat_callers.keys():
                    repeat_callers[phone_numbers[i][0]] = [phone_numbers[i][1], phone_numbers.count(phone_numbers[i])]
                    print(f"{phone_numbers[i][0]} called {phone_numbers[i][1]} {phone_numbers.count(phone_numbers[i])} times")
    #send_email(repeat_callers)
    #os.remove(file_path)
    print(repeat_callers)
    #print("Repeat calls report removed.")

def main():
    if check_for_files():
        os.chdir(DIRECTORY)
        try:
            with open(file_path, 'rb') as target_file:
                response = requests.post(target_url, files={"file": target_file})

            if response.ok:
                print("Upload complete")
                print(f'{file_path} processed successfully.')                
                print(response.text)
                os.remove(file_path)
                print("Report removed.")
            else:
                print(f"Something went wrong: {response.status_code}")
                print(file_path)

        except FileNotFoundError:
            print(f"Error: The file '{file_path}' was not found.")
        except Exception as e:
            print(f"An error occurred: {e}")

def send_email(repeat_callers):
    destination = TO
    msg_text = f"""\
Subject: This Week's Winning Agents!

"""

    with smtplib.SMTP(SERVER, PORT, timeout = 20) as server:
        server.ehlo()
        server.sendmail(from_addr = FROM, to_addrs= destination, msg = msg_text)
        server.quit()
        print("Email with winners has been sent!")


while True:
    main()
    time.sleep(1200)