Call Recovery Platform for our Call Center

On the agents' side:

  They're met with a drop-down menu where, if their queue has abandoned calls (that is, callers reached the queue but hung up before getting to an agent), they would select their queue and hit submit.
  From here, they would see a list of calls that state what queue it was for, what day and time the call came in, and the phone number. There is also some statistics about their clinic and a gauge to visualize how well they're doing. 
  Once the agent returns the call, they would check the box next to the call (or multiple calls if they did more than one) and press submit.
  On the backend, this removes the call from the list (sets the "returned" column in a PostgreSQL DB to "True") and that is it.
  If they are done with all the calls currently in the list of calls to be returned for their queue, they are booted back to queue selection screen.

On my/management's side:

  There is another endpoint where we are able to upload spreadsheets (provided by the CUIC reporting system). 
  Very recently I automated this upload process using a sister script (also provided, "file_scanner.py") but it utilizes the same endpoint.
  The script automatically parses these and adds new calls to the database. Whether or not they get added is determined by Cisco's "Contact Disposition" field, where a 1 indicates the caller disconnected before talking to an agent and 2 means the call was handled by an agent.
  These additions can immediately be accessed by the agents due to how the endpoints work and how they query the database in order to assemble the HTML. 

Landing page:

<img width="832" height="716" alt="image" src="https://github.com/user-attachments/assets/24341f39-e3de-4708-a0eb-8c0c34599518" />

Sample clinic view, demonstrating return rate gauge:

<img width="1503" height="896" alt="image" src="https://github.com/user-attachments/assets/8557dbb2-51ba-4dd9-9559-802bf83ea147" />

Weekly Performance Dashboard:

<img width="1459" height="792" alt="image" src="https://github.com/user-attachments/assets/9542116e-0107-429f-920c-a9b150caaec6" />
