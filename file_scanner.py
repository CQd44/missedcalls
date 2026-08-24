import requests
import os
import time
import smtplib
import csv

target_url = "http://10.200.23.99:13798/process"
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

while True:
    main()
    time.sleep(1200)