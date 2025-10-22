Extremely basic and probably poorly done way I've schemed up to help agents in our call center keep track of calls they need to return.

On the agents' side:

  They're met with a drop-down menu where, if their queue has abandoned calls (that is, callers reached the queue but hung up before getting to an agent), they would select their queue and hit submit.
  From here, they would see a list of calls that state what queue it was for, what day and time the call came in, and the phone number.
  Once the agent returns the call, they would check the box next to the call (or multiple calls if they did more than one) and press submit.
  On the backend, this removes the call from the list (sets the "returned" column in a PostgreSQL DB to "True") and that is it.
  If they are done with all the calls currently in the list of calls to be returned for their queue, they are booted back to queue selection screen.

On my/management's side:

  There is another endpoint where we are able to upload spreadsheets (provided by the CUIC reporting system). 
  The script automatically parses these and adds new calls to the database. Whether or not they get added is determined by Cisco's "Contact Disposition" field, where a 1 indicates the caller disconnected before talking to an agent and 2 means the call was handled by an agent.
  These additions can immediately be accessed by the agents due to how the endpoints work and how they query the database in order to assemble the HTML. 

Again, this was thrown together in a couple of days and there's probably more elegant solutions to this. However, this works perfectly for what the intended use is and it allows us to provide better service to callers by ensuring that we are reaching out and providing care to everyone who calls in. 
