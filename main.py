#abandoned call uploader and verifier
#agents use this to verify calls they've returned, i use it to upload files to populate those lists
#port 13798

import psycopg2
from fastapi import FastAPI, Request, Form, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Generator, List, Tuple
import toml
import os
import openpyxl
import aiofiles
import csv
from datetime import datetime
from pydantic import BaseModel
import socket
from icecream import ic
from urology_aid import handle_xlsx

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static") #logo and favicon go here

HEADERS = ['Queue Name', 'Call Time', 'Contact Disposition', 'Phone Number']
CONFIG = toml.load("./config.toml") # load variables from toml file
CONNECT_STR = f'dbname = {CONFIG['credentials']['dbname']} user = {CONFIG['credentials']['username']} password = {CONFIG['credentials']['password']} host = {CONFIG['credentials']['host']}'
input_file = 'temp_files\\temp_file.csv'

class UrologyStats():
    calls_presented: int = 0
    calls_handled: int = 0
    presented_dict: dict = {}
    handled_dict: dict = {}
    input_file = 'temp_files\\temp_file.csv'

class SelectedRows(BaseModel):
    selectedRows: List[Tuple[str, str]]

@app.on_event("startup")
async def startup_event():
    try:
        init_db()
    except Exception as e:
        print(e)

@app.get("/")
async def clinic_selection(request: Request) -> HTMLResponse:
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()
    html_content = ''' <!DOCTYPE html>
<html>
<head><meta http-equiv="refresh" content="300"> <!-- Auto-refresh every 5 minutes -->
<style>
	body {
		margin: 0;
		display: grid;
		min-height: 10vh;
		place-items: center;
		background-color: lightgray;
	}

	div {
		text-align: center;
	}

	input[type="submit"] {
	display: block;
	margin: 0 auto;
	}

	input[type="text"] {
	display: block;
	margin: 0 auto;
	}

	textarea[name="instructions"] {
	display: block;
	margin: 0 auto;
	}

	textarea {
  width: 320px;
  height: 100px;
	}

	input[type="number"] {
	display: block;
	margin: 0 auto;
	}

	.queue {
	display: block;
	margin: 0 auto;
	}
		</style>
<title>Queue Selection</title></head>
<link rel="icon" type = "image/x-icon" href="/static/favicon.ico">
<body>
    <h1>Queue Selection</h1>
	<div><img src="/static/dhr-logo.png" alt = "DHR Logo" width = "50%" height = "50%"></div>
    <div>
    <p>Please select your queue from the dropdown list. If your queue isn't listed, it currently doesn't have any calls to return, but please check back later.</p>
    <p>New calls are uploaded to this page every morning when I (Clay) get to work, again at 11 AM, and then once more at 4 PM.</p>
    <p>The first upload catches the previous day's abandoned calls from 4-5 PM, the next one captures the current day's abandoned calls up to 11 AM, 
    and then of course the final upload of the day captures the calls between 11 AM and 4 PM.</p>
    <p>This page also refreshes automatically every 5 minutes.</p>
    <p>Queue:</p>
    </div>
	<form method="get" action="/getlist">
		
		<select name="queue" id="queue" class="queue">
'''

    QUERY = '''SELECT DISTINCT(queue) FROM missedcalls WHERE (returned = False AND (date(time) >= date_trunc('week', CURRENT_DATE)
        AND date(time) < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days'));'''
    cur.execute(QUERY)
    results = cur.fetchall()
    queues = [item[0] for item in results]
    queues.sort()

    for queue in queues:
        html_content += f'<option value="{queue}">{queue}</option>'

    html_content += '''</select>
    <input type="submit" id="submitbtn" value="Submit">
    </form>
'''
   
    return HTMLResponse(content = html_content)

@app.get("/getlist")
async def clinic_list(request: Request, queue: str):
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()
    QUERY = '''SELECT * FROM missedcalls WHERE (queue = %s AND returned = False AND (date(time) >= date_trunc('week', CURRENT_DATE)
        AND date(time) < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days'));'''
    DATA = (queue, )
    cur.execute(QUERY, DATA)
    results = cur.fetchall()
    if len(results) == 0:
        cur.close()
        con.close()
        return RedirectResponse(url="/")

    html_content = """
    <html>
        <head>
            <meta http-equiv="refresh" content="600"> <!-- Auto-refresh every 10 minutes -->
        <style>
    h2 {
    font-size: 40px;
    }
    body {
		margin: 0;
        padding: 0;
		place-items: center;
		background-color: lightgray;
	}
	div {
		text-align: center;
        line-height: 1;
        margin: 0;
        padding: 0;
	}

	p, button {
		text-align: center;
        margin: 0;
        padding: 0;
        line-height: 1;
	}
    th, tr {
    padding-right: 15;
    padding-left: 15;
    text-align: center;
    border: solid;
    font-size: 24px;
    }

    td {
    background-color: white;
    border: 2px solid;
    white-space: pre-line;
    text-align : center;}

            </style>
            <title>%s Missed Calls</title>
        </head>
        <link rel="icon" type = "image/x-icon" href="/static/favicon.ico">
        <body>
        <div><img src="/static/dhr-logo.png" alt = "DHR Logo" width = "320px" height = "87.5px"></div>
        <div><h2>Abandoned Call Log for %s (as of %s) on %s</h2></div> 
        <div>When you return a call, check the box next to the call you returned, then click "Submit" <b>ONLY ONCE</b>.</div>
        <div>It may take a second or two for the page to reload and for your submissions to be reflected, so please be patient.</div>       
        <div>When the last call is cleared, you will be taken back to the Queue Selection page.</div>
        <br>
        <div>If you don't see the "Submit" button, try scrolling down.</div>
        <br>
        <form id="dynamicForm" method="post" action="/clearcalls">
<table style="text-align: center; align-items: center;">
                <tr>
                    <th>Queue Name(s)</th>
                    <th>Date and Time of Call</th>
                    <th>Phone Number</th>
                    <th>Returned?</th>
                </tr>
    """ % (queue, queue, datetime.now().strftime("%I:%M %p"), datetime.today().strftime("%m/%d/%Y"))

    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()

    QUERY = '''SELECT * FROM missedcalls WHERE (queue = %s 
    AND returned = False 
    AND (date(time) >= date_trunc('week', CURRENT_DATE)
        AND date(time) < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days'))    
    ORDER BY phone;'''
    DATA = (queue, )

    cur.execute(QUERY, DATA)
    results = cur.fetchall() # list of tuples

    calls = [item for item in results]
    try:
        for call in calls:
            if call[-1] == True:
                continue
            else:
                html_content += f"""
                        <tr>                        
                            <td>{call[0]}</td>
                            <td>{call[1]}</td>
                            <td>{call[2]}</td>
                            <td> <input type="checkbox" data-id="{call[1]}" name="selectedRows"  data-name="{call[2]}">
                <label for="returned"></label><br></td>
                        </tr>
                """
        html_content += '''</table>
        <div><input type="submit" id="submitbtn" value="Submit"></div>
        </form>
        <div><a href="/">Go back to queue selection</a></div>
        <script>
            
                document.getElementById("dynamicForm").addEventListener("submit", async (event) => {
        event.preventDefault(); 

            // Collect checked checkboxes
            const checkboxes = document.querySelectorAll('input[name="selectedRows"]:checked');
            const selectedData = Array.from(checkboxes).map(checkbox => [
                checkbox.dataset.id,
                checkbox.dataset.name
            ]);

            // Get the form's action URL
            const form = document.getElementById("dynamicForm");
            const endpoint = form.action;

            try {
                const response = await fetch(endpoint, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ selectedRows: selectedData })
                });

                if (response.ok) {
                    const result = await response.json();
                    console.log("Server response:", result);
                    window.location.href = window.location.href;
                    // Optionally redirect or update UI based on response
                } else {
                    console.error("Error submitting data:", response.statusText);
                    window.location.href = window.location.href;
                }
            } catch (error) {
                console.error("Network error:", error);
                window.location.href = window.location.href;
            }
        });

        </script>
        </body>
    </html>

        '''
        return HTMLResponse(content=html_content)
    except:
        return HTMLResponse(content="No missed calls here!")
# where I upload the spreadsheet that has all the abandoned calls 
@app.get("/upload")
async def upload_calls(request: Request) -> HTMLResponse:
    html_content = """
<html>
<head>
<style>
	body {
		margin: 0;
		display: grid;
		min-height: 10vh;
		place-items: center;
		background-color: lightgray;
	}
	div {
		text-align: center;
	}

	p, button {
		text-align: center;
	}

	a.button {
    padding: 1px 6px;
    border: 1px outset buttonborder;
    border-radius: 3px;
    color: black;
    background-color: gainsboro;
    text-decoration: none;
}

.from {
	display: inline-flex;
}

</style>

        <title>Call Report Upload</title></head>
<link rel="icon" type = "image/x-icon" href="/static/favicon.ico">
<body>    
	<div><img src="/static/dhr-logo.png" alt = "DHR Logo" width = "320" height = "88"></div>
	<h1>Call Upload</h1>
    <p>Upload abandoned call report.</p>
	
	<form method="post" enctype="multipart/form-data" action="/process">
  <label for="file">File:</label>
  <div><input id="file" name="file" type="file" accept=".xlsx, .csv"/><br><br></div>
  <div><button type="submit" value="submit" class="file" disabled>Upload</button></div>
</form>
	</div>
	<br><br><br>

	<div class="reports">
		<h3>Run Abandoned Call Report</h3>
		<form method="post" action="/report">
		<p>From:</p>
		<div class="from">
		<select name="month_from" id="month_from" required class="month_from">
			<option value="1">January</option>
			<option value="2">February</option>
			<option value="3">March</option>
			<option value="4">April</option>
			<option value="5">May</option>
			<option value="6">June</option>
			<option value="7">July</option>
			<option value="8">August</option>
			<option value="9">September</option>
			<option value="10">October</option>
			<option value="11">November</option>
			<option value="12">December</option>
		</select>
		<select name="day_from" id="day_from" required class="day_from">
			<option value="1">1</option>
			<option value="2">2</option>
			<option value="3">3</option>
			<option value="4">4</option>
			<option value="5">5</option>
			<option value="6">6</option>
			<option value="7">7</option>
			<option value="8">8</option>
			<option value="9">9</option>
			<option value="10">10</option>
			<option value="11">11</option>
			<option value="12">12</option>
			<option value="13">13</option>
			<option value="14">14</option>
			<option value="15">15</option>
			<option value="16">16</option>
			<option value="17">17</option>
			<option value="18">18</option>
			<option value="19">19</option>
			<option value="20">20</option>
			<option value="21">21</option>
			<option value="22">22</option>
			<option value="23">23</option>
			<option value="24">24</option>
			<option value="25">25</option>
			<option value="26">26</option>
			<option value="27">27</option>
			<option value="28">28</option>
			<option value="29">29</option>
			<option value="30">30</option>
			<option value="31">31</option>
			</select>
		<select name="year_from" id="year_from" required class="year_from">
			<option value="2025">2025</option>
			<option value="2026">2026</option>
		</select>
		</div>	
				<p>To:</p>
		<div class="from">
		<select name="month_to" id="month_to" required class="month_to">
			<option value="1">January</option>
			<option value="2">February</option>
			<option value="3">March</option>
			<option value="4">April</option>
			<option value="5">May</option>
			<option value="6">June</option>
			<option value="7">July</option>
			<option value="8">August</option>
			<option value="9">September</option>
			<option value="10">October</option>
			<option value="11">November</option>
			<option value="12">December</option>
		</select>
		<select name="day_to" id="day_to" required class="day_to">
			<option value="1">1</option>
			<option value="2">2</option>
			<option value="3">3</option>
			<option value="4">4</option>
			<option value="5">5</option>
			<option value="6">6</option>
			<option value="7">7</option>
			<option value="8">8</option>
			<option value="9">9</option>
			<option value="10">10</option>
			<option value="11">11</option>
			<option value="12">12</option>
			<option value="13">13</option>
			<option value="14">14</option>
			<option value="15">15</option>
			<option value="16">16</option>
			<option value="17">17</option>
			<option value="18">18</option>
			<option value="19">19</option>
			<option value="20">20</option>
			<option value="21">21</option>
			<option value="22">22</option>
			<option value="23">23</option>
			<option value="24">24</option>
			<option value="25">25</option>
			<option value="26">26</option>
			<option value="27">27</option>
			<option value="28">28</option>
			<option value="29">29</option>
			<option value="30">30</option>
			<option value="31">31</option>
			</select>
		<select name="year_to" id="year_to" required class="year_to">
			<option value="2025">2025</option>
			<option value="2026">2026</option>
		</select>
	</div>
	<br><br> <input type="submit" id="submitbtn" value="Submit">
	</form>
	</div>
    
    <script>
	 document.querySelector("input[type=file]").onchange = ({
      target: { value },
    }) => {
      document.querySelector("button[type=submit]").disabled = !value;
	};

</script>

</body>
<!-- Why are you looking at this? :)  ~ Clay-->
</html>
"""
    return HTMLResponse(content=html_content)

# Process uploaded spreadsheet. Currently works just as intended. Proooobably could be more efficient.
@app.post("/process", response_class=HTMLResponse)
async def process_file(file: UploadFile):
    if file.filename[-1] == 'x' and file.filename[:5] != 'Agent':
        if not os.path.exists(f'temp_files\\{file.filename}'):
            try:
                contents = await file.read()
                async with aiofiles.open(f"temp_files\\{file.filename}", 'wb') as f: # type: ignore
                    await f.write(contents)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f'Something went wrong. Tell Clay! {e}')
            finally:
                await file.close()
            wb = openpyxl.load_workbook(filename= f'temp_files\\{file.filename}', data_only=True) 
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
    elif file.filename[-1] == 'x' and file.filename[:5] == 'Agent':        
        ic("Urology file detected")
        if not os.path.exists(f'temp_files\\{file.filename}'):
            try:
                contents = await file.read()
                async with aiofiles.open(f"temp_files\\{file.filename}", 'wb') as f: # type: ignore
                    await f.write(contents)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f'Something went wrong. Tell Clay! {e}')
            finally:
                await file.close()
        handle_xlsx(f"temp_files\\{file.filename}")
        UrologyStats.input_file = "temp_files\\urology_output.csv"
    
    if file.filename[-1] == 'v':
         if not os.path.exists(f'temp_files\\{file.filename}'):
            try:
                contents = await file.read()
                async with aiofiles.open("temp_files\\temp_file.csv", 'wb') as f: # type: ignore
                    await f.write(contents)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f'Something went wrong. Tell Clay! {e}')
            finally:
                await file.close()

    def row_generator() -> Generator:     
        with open(UrologyStats.input_file, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                try:
                    yield row
                except Exception as e:
                    print("Invalid row.\n", e)

    row_gen = row_generator()
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()        
    cur.execute("SELECT queue, time, phone FROM missedcalls;")
    cached_rows: list[tuple] = cur.fetchall()
    processed_rows = []
    rows_added = 0
    datetime_format = "%m/%#d/%y %#I:%M:%S %p"
    for row in cached_rows:
        tuple_to_append = (row[0], datetime.strftime(row[1], datetime_format), str(row[2]))
        processed_rows.append(tuple_to_append)
    # 10/05/25 4:08:36 PM for time format. note the lack of a leading 0 for the hour and two digit year!
    for row in row_gen:
            ic(UrologyStats.input_file)
            row_values: tuple[str, str, int] = (row['Queue Name'], str(row['Call Time']), row['Phone Number'])      
            if row_values in processed_rows:
                print("Call already in database:", row_values)
                continue
            else:
                if row['Contact Disposition'] in {'1', '1.0'}:            
                    QUERY = "INSERT into missedcalls (queue, time, phone) VALUES (%s, %s, %s) ON CONFLICT (queue, time, phone) DO NOTHING;"
                    try:
                        DATA = (row['Queue Name'], row['Call Time'], int(row['Phone Number']))                      
                        cur.execute(QUERY, DATA)                        
                        rows_added += 1
                    except Exception as e:
                        print(row)
                        print("Phone number was probably not a phone number.\n")
                        print("Phone number: ", row['Phone Number'],"\n", e)
        
    cur.close()
    con.commit()
    con.close()

    try:
        files = os.listdir("temp_files")
        for file in files:
            os.remove(f'temp_files\\{file}')
    except:
        pass
    if rows_added == 0:
        return HTMLResponse(content="File uploaded and processed successfully. No new calls were added to the database.")
    else:
        return HTMLResponse(content=f"File uploaded and processed successfully. {rows_added} new calls were added to the database.")

@app.post("/report") #Allows user to download a report. Report is mostly static except for the date range.
async def run_report(month_from: int = Form(...), day_from: int = Form(...), year_from: int = Form(...), month_to: int = Form(...), day_to: int = Form(...), year_to: int = Form(...)) -> FileResponse:
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()

    from_date = str(year_from) + "-" + str(month_from) + "-" + str(day_from)
    to_date = str(year_to) + "-" + str(month_to) + "-" + str(day_to)

    print(from_date)

    if datetime.strptime(to_date, '%Y-%m-%d') < datetime.strptime(from_date, '%Y-%m-%d'):
        html_content="""
<html>
        <head>            
            <style>
            body {
		margin: 0;
		display: grid;
		place-items: center;
		background-color: lightgray;
	}
	div {
		text-align: center;
	}

	p, button {
		text-align: center;
	}
            </style>
        </head>
        <link rel="icon" type = "image/x-icon" href="/static/favicon.ico">
        <body>
        <div><img src="/static/dhr-logo.png" alt = "DHR Logo" width = "320px" height = "87.5px"></div>
            <h2>Report range error!</h2>
            <p>Please go back and check your report range and make sure the "From" date is before or the same as the "To" date</p>
            <p><div><a href="/" class="active">Go back</a></div>
            </body>
            </html>            
            """
        return HTMLResponse(content=html_content) # type: ignore

    with open('callbacks_report.csv', 'w', newline = '') as output:
        header_row = ['Queue', 'Date and Time of Call', 'Phone Number', 'Returned', 'Returned On', 'IP Address', 'PC Name']
        QUERY = "SELECT * FROM missedcalls WHERE (DATE(time) >= %s AND DATE(time) <= %s);"
        DATA = (from_date, to_date)
        cur.execute(QUERY, DATA)
        results = cur.fetchall()
        writer = csv.writer(output)
        writer.writerow(header_row)
        writer.writerows(results)

    cur.close()
    con.close()    
    return FileResponse(path='.\callbacks_report.csv', status_code=200, media_type="csv", filename="callbacks_report.csv") # type: ignore

@app.post("/clearcalls", response_class=HTMLResponse)
async def clear_calls(request: Request, data: SelectedRows):
    client_ip = request.client.host
    hostname = get_hostname(client_ip)
    selected_rows = data.selectedRows
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()

    QUERY = "UPDATE missedcalls SET returned = True, returned_on = CURRENT_TIMESTAMP(0), ip_address = %s, hostname = %s WHERE (time = %s AND phone = %s);"
    
    print("Calls marked as returned: ", len(selected_rows))

    for call in selected_rows:
        DATA = (client_ip, hostname, call[0], call[1])
        cur.execute(QUERY, DATA)

    cur.close()
    con.commit()

    return HTMLResponse(content="How did you see this? Tell Clay what you did to get to this message!")

def get_hostname(ip_address):
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except socket.herror:
        return "No hostname found"

def init_db():
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor() 
    cur.execute("""CREATE TABLE IF NOT EXISTS missedcalls 
                (queue TEXT,
                time TIMESTAMP,
                phone BIGINT,
                returned BOOLEAN DEFAULT FALSE,
                returned_on TIMESTAMP DEFAULT NULL,
                ip_address INET,
                hostname TEXT, 
                UNIQUE (queue, time, phone)
                );"""
            )
    cur.close()
    con.commit()