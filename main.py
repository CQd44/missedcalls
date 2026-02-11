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
import math

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static") #logo and favicon go here

HEADERS = ['Queue Name', 'Call Time', 'Contact Disposition', 'Phone Number']
CONFIG = toml.load("./config.toml") # load variables from toml file
CONNECT_STR = f'dbname = {CONFIG['credentials']['dbname']} user = {CONFIG['credentials']['username']} password = {CONFIG['credentials']['password']} host = {CONFIG['credentials']['host']}'

class InputSpreadsheet():
    input_file: str = 'temp_files\\temp_file.csv'

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
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <title>Queue Selection</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link href="https://fonts.googleapis.com" rel="stylesheet">
    <style>
        :root {
            --brand-primary: #00a9a7;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #334155;
            --border: #e2e8f0;
        }

        body {
            margin: 0;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: var(--bg);
            color: var(--text-main);
            font-family: 'Roboto', sans-serif;
            line-height: 1.6;
        }

        .logo-container {
            text-align: center;

            width: 100%;
            margin-bottom: 10px;
        }

        h1 {
            color: var(--brand-primary);
            font-size: 2rem;
            margin-bottom: 20px;
        }

        /* Consistent Card Style */
        .queue-card {
            background: var(--card-bg);
            padding: 2.5rem;
            border-radius: 12px;
            border-top: 4px solid var(--brand-primary);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 700px;
            text-align: center;
        }

        .info-text {
            font-size: 0.95rem;
            color: #64748b;
            text-align: left;
            margin-bottom: 25px;
            background-color: #f1f5f9;
            padding: 20px;
            border-radius: 8px;
        }

        .info-text p {
            margin: 10px 0;
        }

        /* Form Elements */
        label {
            display: block;
            font-weight: 700;
            margin-bottom: 10px;
            color: var(--brand-primary);
        }

        select.queue {
            width: 100%;
            max-width: 400px;
            padding: 12px;
            border: 1.5px solid var(--border);
            border-radius: 8px;
            font-size: 1rem;
            margin-bottom: 20px;
            background-color: white;
            outline-color: var(--brand-primary);
        }

        input[type="submit"] {
            display: inline-block;
            padding: 12px 30px;
            background-color: var(--brand-primary);
            color: white;
            border: 2px solid var(--brand-primary);
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            font-size: 1rem;
        }

        input[type="submit"]:hover {
            background-color: white;
            color: var(--brand-primary);
        }

        .card-footer {
    margin-top: 15px;
    padding-top: 20px;
    border-top: 1px solid var(--border); /* Subtle divider line */
    width: 100%;
    display: flex;
    justify-content: center;
}

/* Updated button style for the footer */
.button-footer {
    display: inline-block;
    padding: 10px 20px;
    background-color: var(--brand-primary);
    color: white !important;
    text-decoration: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.2s ease;
    width: 80%; /* Makes the button nice and clickable */
    text-align: center;
}

.button-footer:hover {
    background-color: #008f8d; /* Slightly darker teal on hover */
    transform: translateY(-1px);
}
    </style>
</head>

<body>
    <div class="logo-container">
        <img src="/static/dhr-logo.png" alt="DHR Logo" width="320px">
    </div>

    <h1>Call Recovery Queue Selection</h1>

    <div class="queue-card">
        <div class="info-text">
            <p>Please select your queue from the dropdown list. This tool only shows missed calls from the <strong>current day</strong>.</p>
            <p>If your queue isn't listed, it currently doesn't have any calls to return, but please check back later.</p>
            <p><small>Note: Calls are refreshed hourly. This page auto-refreshes every 5 minutes.</small></p>
        </div>

        <form method="get" action="/getlist">
            <label for="queue">Select Queue:</label>
            <select name="queue" id="queue" class="queue">
'''

    QUERY = '''SELECT DISTINCT(queue) FROM missedcalls WHERE (returned = False AND date(time) = CURRENT_DATE);'''
    cur.execute(QUERY)
    results = cur.fetchall()
    queues = [item[0] for item in results]
    queues.sort()

    for queue in queues:
        html_content += f'<option value="{queue}">{queue}</option>'

    html_content += '''</select>
    <input type="submit" id="submitbtn" value="Submit">
    </form>
    <div class="card-footer">
        <a class="button-footer" href="/dashboard">Overall Performance Dashboard →</a>
    </div> 
    </div>
    </body>
    </html>
'''
   
    return HTMLResponse(content = html_content)

@app.get("/getlist")
async def clinic_list(request: Request, queue: str):
    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()
    QUERY = '''SELECT * FROM missedcalls WHERE (queue = %s AND returned = False AND date(time) = CURRENT_DATE);'''
    DATA = (queue, )
    cur.execute(QUERY, DATA)
    results = cur.fetchall()
    if len(results) == 0:
        cur.close()
        con.close()
        return RedirectResponse(url="/")

    html_content = """
    <!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="600">
    <title>%s Missed Calls</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link href="https://fonts.googleapis.com" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-3.3.0.min.js" charset="utf-8"></script>
    <style>
        :root {
            --brand-primary: #00a9a7;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #334155;
            --border: #e2e8f0;
        }

        body {
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: var(--bg);
            color: var(--text-main);
            font-family: 'Roboto', sans-serif;
        }

        /* Sticky Header Section */
        .page-header {
            position: sticky;
            top: 0;
            z-index: 100;
            background-color: var(--bg);""" % (queue, )
    html_content += "width: 100%; text-align: center; padding-bottom: 10px; border-bottom: 1px solid var(--border);        }"
    html_content += """
        h2 {
            color: var(--brand-primary);
            margin: 5px 0;
            font-size: 1.8rem;
        }

        .instructions {
            max-width: 900px;
            font-size: 0.9rem;
            color: #64748b;
            margin: 15px 0;
            text-align: center;
        }

        /* Layout for the two main cards */
        .table-container {
            display: flex;
            justify-content: center;
            gap: 25px; """
    html_content += "width: 100%;max-width: 1400px;align-items: flex-start;flex-wrap: wrap;}"
    html_content += """

        /* Modern Card Styling */
        .card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 12px;
            border-top: 4px solid var(--brand-primary);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }

        .main-log-card { flex: 2; min-width: 600px; }
        .stats-card { flex: 1; min-width: 350px; position: sticky; top: 180px; }

        /* Table Styling */
        """
    html_content += "table {            width: 100%;            border-collapse: collapse;            margin-bottom: 15px;        }"
    html_content += """
        th {
            background-color: #f8fafc;
            color: var(--brand-primary);
            font-size: 0.85rem;
            text-transform: uppercase;
            padding: 12px;
            border-bottom: 2px solid var(--border);
            position: sticky;
            top: 0;
            z-index: 5;
        }

        td {
            padding: 12px;
            border-bottom: 1px solid var(--border);
            text-align: center;
            font-size: 0.95rem;
        }

        /* Submit Button */
        input[type="submit"] {
            background-color: var(--brand-primary);
            color: white;
            border: 2px solid var(--brand-primary);
            padding: 10px 30px;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
        }

        input[type="submit"]:hover {
            background-color: white;
            color: var(--brand-primary);
        }

        /* Go Back Button */
        a.button {
            display: inline-block;
            text-decoration: none;
            color: var(--brand-primary);
            font-weight: 600;
            margin-bottom: 15px;
            padding: 5px 10px;
            border: 1px solid var(--brand-primary);
            border-radius: 6px;
            transition: 0.2s;
        }

        a.button:hover {
            background-color: var(--brand-primary);
            color: white;
        }

        .card-footer {
    margin-top: 15px;
    padding-top: 20px;
    border-top: 1px solid var(--border); /* Subtle divider line */
    width: 100% ;
    display: flex;
    justify-content: center;
}

/* Updated button style for the footer */
.button-footer {
    display: inline-block;
    padding: 10px 20px;
    background-color: var(--brand-primary);
    color: white !important;
    text-decoration: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.9rem;
    transition: all 0.2s ease;
    width: 80%; /* Makes the button nice and clickable */
    text-align: center;
}

.button-footer:hover {
    background-color: #008f8d; /* Slightly darker teal on hover */
    transform: translateY(-1px);
}


"""
    html_content+= "#myGauge { width: 100%; height: auto;}"
    html_content += """
    </style>
</head>

<body>
    <div class="page-header">
        <img src="/static/dhr-logo.png" alt="DHR Logo" width="240px">
        <h2>Abandoned Call Log for %s</h2>
        <p style="margin: 0; color: #64748b; font-size: 0.8rem;">As of %s on %s</p>
    </div>

    <div class="instructions">
        Numbers are clickable (Open with Jabber). Check the box when a call is returned and click <strong>Submit</strong> once. 
        When the last call is cleared, you'll return to the Queue Selection.
    </div>

    <div class="table-container">
        <!-- Main Log Card -->
        <div class="card main-log-card">
            <form id="dynamicForm" method="post" action="/clearcalls">
                <table>
                    <thead>
                        <tr>
                            <th>Queue Name(s)</th>
                            <th>Date/Time</th>
                            <th>Phone Number</th>
                            <th>Dialed Number</th>
                            <th>Returned?</th>
                        </tr>
                    </thead>
                    <tbody>
    """ % (queue,  datetime.now().strftime("%I:%M %p"), datetime.today().strftime("%m/%d/%Y"))

    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()

    QUERY = '''SELECT queue, time, phone, dialed FROM missedcalls WHERE queue = %s 
    AND returned = False 
    AND date(time) = CURRENT_DATE    
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
                            <td><a href="tel:{call[2]}">{call[2]}</a></td>
                            <td>{call[3]}</td>
                            <td> <input type="checkbox" data-id="{call[1]}" name="selectedRows"  data-name="{call[2]}">
                <label for="returned"></label><br></td>
                        </tr>
                """
    
        html_content += f'''
        </tbody>
        </table>
            <div style="text-align: right;">
                    <input type="submit" id="submitbtn" value="Submit Changes">
                </div>
            </form>
        </div>

        <div class="card stats-card">
            
            
            <table>
                <caption style="font-weight: bold; margin-bottom: 10px; color: var(--brand-primary);">{queue} Weekly Performance</caption>
                <thead>
                    <tr>
                        <th>Abandoned</th>
                        <th>Returned</th>
                        <th>Rate</th>
                    </tr>
                </thead>
                <tbody>
                '''
    
        QUERY = """SELECT
                COUNT(*) as missed_calls,
                COUNT(CASE WHEN returned = True THEN 1 END) AS returned_calls
                FROM
                missedcalls
                WHERE (queue = %s
                AND
                (date(time) >= date_trunc('week', CURRENT_DATE)
        AND date(time) < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days'));
                """

        DATA = (queue, )
        cur.execute(QUERY, DATA)
        results = cur.fetchall()
        
        for result in results:
            return_rate = "-"
            if result[0] != 0:
                return_rate = math.ceil(100 * (result[1] / result[0]))
            html_content += f"""
                    <tr>
                        <td>{result[0]}</td>
                        <td>{result[1]}</td>
                        <td>{return_rate}%</td>
                    </tr>                        
                    """
        html_content += """ 
        </tbody>
        </table>
                    <br><br>
                    <div style="background-color: lightgray;" id="myGauge"></div>
                    <div class="card-footer">
        <a class="button-footer" href="/">← Back to Selection</a>
    </div> 
                      
                    </div>
                    
        <script>                
            var currentValue = %s;

            var data = [{
                domain: { x: [0, 1], y: [0, 1] },
                value: currentValue,
                // Update the title format with the actual value if needed
                title: { text: "Call Recovery Rate"}, 
                type: "indicator",
                mode: "gauge+number",
                gauge: {
                bgcolor: "white",
                borderwidth: 0,
                    axis: {
                        range: [0, 100], // Set the range from 0 to 100
                        tickvals: [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
                    },
                    bar: {color: "black", thickness: 0.1},
                    steps: [
                        { range: [0, 70],   color: "red"},
                        { range: [70, 90],  color: "orange" },
                        { range: [90, 100], color: "green" }	
                    ],
                    threshold: {
                        line: { color: "black", width: 4 },
                        thickness: 0.75,
                        value: 90 // Optional: a target threshold
                    }
                }
            }];

            function valueToRadians(value) {
                // Reverses the direction (180 deg at 0 value, 0 deg at 100 value)
                return (Math.PI - ((value / 100) * Math.PI) );
            }

            var angle = valueToRadians(currentValue);

            // length of the arrow (normalized coordinates)
            var needleLength = 0.45; // Slightly shorter
            
            // origin point Y for the base of the arrow
            var originY = 0.25; 

            // Calculate the end points of the arrow based on the angle
            var arrowEndX = 0.5 + (needleLength * Math.cos(angle));
            var arrowEndY = originY + (needleLength * Math.sin(angle));

            // Chart layout configuration
            var layout = {
                autosize: true,
                yaxis: { scaleanchor: "x" },
                margin: { t: 50, b: 20, l: 30, r: 30 },
                paper_bgcolor: "white",
                plot_bgcolor: "white",
                annotations: [{
                    x: arrowEndX, 
                    y: arrowEndY, 
                    xref: 'paper',
                    yref: 'paper',
                    ax: 0.5, 
                    ay: originY, 
                    axref: 'paper',
                    ayref: 'paper',
                    showarrow: true,
                    arrowhead: 3, 
                    arrowsize: 1,
                    arrowwidth: 3,
                    arrowcolor: 'black',
                    standoff: 0 
                }]
            };

            // Render the gauge chart
            Plotly.newPlot('myGauge', data, layout);
            window.addEventListener('resize', function() {
    Plotly.Plots.resize('myGauge');
    });
            </script>

            <script>
                   document.getElementById("dynamicForm").addEventListener("submit", async (event) => {
        event.preventDefault(); 

            const checkboxes = document.querySelectorAll('input[name="selectedRows"]:checked');
            const selectedData = Array.from(checkboxes).map(checkbox => [
                checkbox.dataset.id,
                checkbox.dataset.name
            ]);

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
        </html>""" % (return_rate, )        
        return HTMLResponse(content=html_content)
    except:
        return HTMLResponse(content="No missed calls here!")    

@app.get("/dashboard")
async def get_dashboard(request: Request) -> HTMLResponse:
    html_content = """
    <!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <title>Abandoned Call Recovery Dashboard</title>
    <link rel="icon" type="image/x-icon" href="/static/favicon.ico">
    <link href="https://fonts.googleapis.com" rel="stylesheet">
    <script src="https://cdn.plot.ly/plotly-3.3.0.min.js" charset="utf-8"></script>
    <style>
        :root {
            --brand-primary: #00a9a7;
            --bg: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #334155;
            --border: #e2e8f0;
        }

        body {
            margin: 0;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            background-color: var(--bg);
            color: var(--text-main);
            font-family: 'Roboto', sans-serif;
        }

        .page-header {
            text-align: center;
            margin-bottom: 30px;"""
    
    html_content += "width: 100% ;"

    html_content += """
        }

        h2 {
            color: var(--brand-primary);
            font-size: 1.8rem;
            margin: 10px 0;
        }

        .table-container {
            display: flex;
            justify-content: center;
            gap: 25px;"""
    
    html_content += "width: 100% ;"

    html_content += """
            max-width: 1400px;
            align-items: flex-start;
            flex-wrap: wrap;
        }

        /* Card Styling */
        .card {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 12px;
            border-top: 4px solid var(--brand-primary);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }

        .main-stats-card { flex: 2; min-width: 600px; }
        .overall-perf-card { flex: 1; min-width: 400px; text-align: center; }

        /* Table Styling */
        table {"""
    
    html_content += "width: 100% ;"

    html_content += """
            border-collapse: collapse;
            margin-bottom: 10px;
        }

        caption {
            font-weight: 700;
            margin-bottom: 15px;
            color: var(--brand-primary);
            font-size: 1.2rem;
        }

        th {
            background-color: #f8fafc;
            color: var(--brand-primary);
            font-size: 1.2rem;
            text-transform: uppercase;
            position: sticky;
            z-index: 10;
            padding: 12px;
            border-bottom: 2px solid var(--border);
        }

        td {
            padding: 12px;
            border-bottom: 1px solid var(--border);
            font-size: 1.5rem;
            text-align: center;
        }

        /* Footer styling for the Back button */
        .card-footer {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid var(--border); """
    
    html_content += "width: 100%;"

    html_content += """
            display: flex;
            justify-content: center;
        }

        .button-footer {
            display: inline-block;
            padding: 10px 24px;
            background-color: var(--brand-primary);
            color: white !important;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;"""
    
    html_content += "width: 80%;}"

    html_content += """

        .button-footer:hover {
            background-color: #008f8d;
            transform: translateY(-1px);
        }"""

    html_content += "#myGauge { width: 100%; }"

    html_content += """
    .main-stats-card {
    flex: 2;
    min-width: 600px;
  //max-height: 80vh; /* Optional: adds a scrollbar to the card itself */
    overflow-y: auto; 
      position: relative;
}

.main-stats-card thead th {
    position: sticky;
    top: 0; /* Sticks to the very top of the viewport */
    z-index: 20;
    background-color: #f8fafc; /* Must have a background to hide scrolling text */
    padding: 15px 10px;
    border-bottom: 2px solid var(--border);
    box-shadow: 0 2px 5px rgba(0,0,0,0.05); /* Adds depth when scrolling */
}
.main-stats-card caption {
    position: sticky;
    top: 0;
    z-index: 21;
    background-color: var(--card-bg);
    padding: 15px 0;
    margin: 0;
}

.main-stats-card thead th {
    top: 50px; 
}
.overall-perf-card {
    flex: 1;
    min-width: 400px;
    position: sticky;
    top: 20px; /* Distance from the top of the viewport when scrolling */
    align-self: flex-start; /* Required for sticky to work inside flexbox */
}
.table-container {
    display: flex;
    justify-content: center;
    gap: 25px;
    width: 100%;
    max-width: 1400px;
    align-items: flex-start; """

    html_content += "width: 100%;"

    html_content += """
    max-width: 1400px;
    align-items: flex-start; /* Crucial: prevents the right card from stretching */
}

        </style>
</head>
<body>
    <div class="page-header">
        <img src="/static/dhr-logo.png" alt="DHR Logo" width="320px">
        <h2>Week to Date Call Recovery Statistics</h2>
        <p style="color: #64748b;">As of %s</p>
    </div>

    <div class="table-container">
        <!-- Main Queue Stats -->
        <div class="card main-stats-card">
            <table>
                <caption>Queue Performance</caption>
                <thead>
                    <tr>
                        <th>Queue</th>
                        <th>Abandoned</th>
                        <th>Returned</th>
                        <th>Return Rate</th>
                    </tr>
                </thead>
                <tbody>
    """ % (datetime.now().strftime("%I:%M %p"),) 

    con = psycopg2.connect(CONNECT_STR)
    cur = con.cursor()

    QUERY = """SELECT 
            queue,
            COUNT(*) AS missed_calls,
            COUNT(CASE WHEN returned = True THEN 1 END) AS returned_calls
            FROM
            missedcalls
            WHERE (date(time) >= date_trunc('week', CURRENT_DATE)
        AND date(time) < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days')
            GROUP BY queue;
            """
    cur.execute(QUERY)
    results = cur.fetchall()
    for result in results:
        if math.ceil(100 * (result[2] / result[1])) >= 90:
            color = 'green'
        else:
            color = 'red'
        html_content += f"""
                <tr>
                    <td>{result[0]}</td>
                    <td>{result[1]}</td>
                    <td>{result[2]}</td>
                    <td style = "color: {color};">{math.ceil(100 * (result[2] / result[1]))}%</td
                </tr>
        """

    html_content += """
    </tbody>
        </table>
    </div>
           <div class="card overall-perf-card">
            <table>
                <caption>Overall Center Performance</caption>
                <thead>
                    <tr>
                        <th>Abandoned</th>
                        <th>Returned</th>
                        <th>Rate</th>
                    </tr>
                </thead>
                <tbody>"""
    
    QUERY = """SELECT
            COUNT(*) as missed_calls,
            COUNT(CASE WHEN returned = True THEN 1 END) AS returned_calls
            FROM
            missedcalls
            WHERE (date(time) >= date_trunc('week', CURRENT_DATE)
        AND date(time) < date_trunc('week', CURRENT_DATE) + INTERVAL '7 days');
            """
    
    cur.execute(QUERY)
    results = cur.fetchall()
    
    for result in results:
        return_rate = "-"
        if result[0] != 0:
            return_rate = math.ceil(100 * (result[1] / result[0]))
        html_content += f"""
                <tr>
                    <td>{result[0]}</td>
                    <td>{result[1]}</td>
                    <td>{return_rate}%</td>
                </tr>                        
            """    
    
    html_content += """
                </tbody>
            </table>
                    <div id="myGauge"></div>

            <div class="card-footer">
                <a class="button-footer" href="/">← Back to Selection</a>
            </div>
        </div>
    </div>

    <script>
        var currentValue = %s;
        var data = [{
            domain: { x: [0, 1], y: [0, 1] },
            value: currentValue,
            title: { text: "Call Recovery Rate", font: { color: '#00a9a7', family: 'Roboto', size: 18 } }, 
            type: "indicator",
            mode: "gauge+number",
            gauge: {
                axis: { range: [0, 100], tickvals: [0, 20, 40, 60, 80, 100] },
                bar: { color: "#334155", thickness: 0.2 },
                bgcolor: "white",
                steps: [
                    { range: [0, 70], color: "#ef4444" },
                    { range: [70, 90], color: "#f59e0b" },
                    { range: [90, 100], color: "#22c55e" }
                ],
                threshold: { line: { color: "black", width: 4 }, value: 90 }
            }
        }];

        // Needle Logic
        var angle = (Math.PI - ((currentValue / 100) * Math.PI));
        var needleLength = 0.45;
        var originY = 0.25; 
        var arrowEndX = 0.5 + (needleLength * Math.cos(angle));
        var arrowEndY = originY + (needleLength * Math.sin(angle));

        var layout = {
            autosize: true,
          //  height: 300,
            margin: { t: 60, b: 20, l: 30, r: 30 },
            paper_bgcolor: "transparent",
            annotations: [{
                x: arrowEndX, y: arrowEndY, xref: 'paper', yref: 'paper',
                ax: 0.5, ay: originY, axref: 'paper', ayref: 'paper',
                showarrow: true, arrowhead: 3, arrowsize: 1, arrowwidth: 3, arrowcolor: 'black'
            }]
        };

        Plotly.newPlot('myGauge', data, layout);

        window.addEventListener('resize', function() {
            Plotly.Plots.resize('myGauge');
        });
    </script>
</body> <!-- Clay was here! :) -->
</html>
""" % (return_rate, )
    cur.close()
    return HTMLResponse(content=html_content)

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
        InputSpreadsheet.input_file = 'temp_files\\temp_file.csv'
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

            with open(InputSpreadsheet.input_file, 'w', newline='') as temp:
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
        InputSpreadsheet.input_file = "temp_files\\urology_output.csv"
    
    if file.filename[-1] == 'v':
         if not os.path.exists(f'temp_files\\{file.filename}'):
            try:
                contents = await file.read()
                async with aiofiles.open(InputSpreadsheet.input_file, 'wb') as f: # type: ignore
                    await f.write(contents)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f'Something went wrong. Tell Clay! {e}')
            finally:
                await file.close()

    def row_generator() -> Generator:     
        with open(InputSpreadsheet.input_file, 'r', encoding='utf-8-sig') as csvfile:
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
            row_values: tuple[str, str, int] = (row['Queue Name'], str(row['Call Time']), row['Phone Number'])      
            if row_values in processed_rows:
                print("Call already in database:", row_values)
                continue
            else:
                if row['Contact Disposition'] in {'1', '1.0'}:            
                    QUERY = "INSERT into missedcalls (queue, time, phone, dialed) VALUES (%s, %s, %s, %s) ON CONFLICT (queue, time, phone) DO NOTHING;"
                    try:
                        DATA = (row['Queue Name'], row['Call Time'], int(row['Phone Number']), int(row['Number Dialed']))                      
                        cur.execute(QUERY, DATA)                        
                        rows_added += 1
                    except Exception as e:
                        print(e)
                        print(row)
                        print(DATA)
                        print("Phone number was probably not a phone number.\n")
        
    cur.close()
    con.commit()
    con.close()

    try:
        files = os.listdir("temp_files")
        for x in files:
            os.remove(f'temp_files\\{x}')
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
    print(data)
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