import csv
import easygui
from icecream import ic
import datetime
import os
import aiofiles
import openpyxl

def handle_xlsx(input):
    calls_presented: int = 0
    calls_handled: int = 0
    presented_dict: dict = {}
    handled_dict: dict = {}
    wb = openpyxl.load_workbook(filename= f'{input}', data_only=True) 
    sheet = wb.worksheets[0]
    reader = sheet.iter_rows(values_only=True)
    first_row_skipped = False
    input_rows: list = []
    for row in reader:
        if row[0] == None:
            if not first_row_skipped:
                first_row_skipped = True
            else:
                break
            continue
        elif row not in input_rows:
            input_rows.append(row)

    with open('temp_files\\temp_file.csv', 'w', newline='') as temp:
        writer = csv.writer(temp)
        for row in input_rows:
            writer.writerow(row)
    previous_row = {}
    with open('temp_files\\temp_file.csv', "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['Extension'] == row['Call ANI'] and row['Called Number'] == '21898':
                calls_presented +=1
                presented_dict[row['Call Start Time']] = previous_row['Call ANI']
            if row['Extension'] != row['Call ANI'] and row['Called Number'] == '21898':
                calls_handled += 1
                handled_dict[row['Call Start Time']] = row['Call ANI']
            previous_row = row

    ic(calls_presented)
    ic(calls_handled)

    presented_numbers: list[str] = list(presented_dict.values())
    handled_numbers: list[str] = list(handled_dict.values())
    abandoned_numbers:dict[str, str] = {}

    for number in presented_numbers:
        call_time = ''
        if number not in handled_numbers and number not in abandoned_numbers:
            for time in presented_dict.keys():
                if number == presented_dict[time]:
                    call_time = time
            abandoned_numbers[call_time] = number

    ic(len(abandoned_numbers))

    with open("temp_Files\\urology_output.csv", 'w', newline='') as output:
        writer = csv.writer(output)
        header = ['Queue Name', 'Call Time', 'Phone Number', 'Contact Disposition']
        writer.writerow(header)
        for time in abandoned_numbers.keys():
            writer.writerow(['URO_SCHL_CSQ', time, abandoned_numbers[time], '1'])

#handle_xlsx(input_xlsx)