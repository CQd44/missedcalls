# Service Recovery Platform

A scalable, multi-clinic call recovery platform designed to optimize healthcare call center operations. `missedcalls` automates the aggregation, tracking, and prioritization of unanswered patient calls, bridging the gap between missed inquiries and proactive outreach.

## 📌 Project Origin & Evolution
The project began with a critical baseline requirement: building a localized solution to track and return missed calls for a single high-volume partner clinic. Recognizing the broader operational bottleneck, the system architecture was refactored and scaled to serve **every clinic managed across our entire call center network**. 

By shifting from a single-clinic feature to a unified infrastructure platform, the tool now prevents patient leakage and significantly reduces callback response lag times across all serviced clinics.

## ✨ Key Features
* **Multi-Tenant Architecture:** Built from the ground up to isolate and manage missed call queues across multiple independent clinics simultaneously.
* **Centralized Tracking Dashboard:** Provides call center agents with a single, structured repository to log and update callback statuses.
* **Intelligent Prioritization:** Enables teams to flag and organize patient call history to avoid duplicated efforts or forgotten follow-ups.
* **Lightweight Performance:** Engineered to process event states with minimal overhead, maintaining high performance during peak traffic hours.

## 📸 Platform Overview

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


## 🛠️ System Architecture & Workflow
1. **Capture:** The system listens for or ingests call records, isolating missed or abandoned events.
2. **Aggregate & Map:** Events are automatically triaged and mapped to their respective clinic profiles within the central database.
3. **Queue Distribution:** The platform serves the updated callback queue to agents based on real-time organizational needs.
4. **Resolution:** Outbound logs track the life cycle of the callback until the patient has been successfully reached.

## 🚀 Getting Started

### Prerequisites
* Ensure you have your standard runtime environment installed (e.g., Node.js / Python / Docker depending on your project core).

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com
   ```
2. Navigate into the project directory:
   ```bash
   cd missedcalls
   ```
3. Install the required dependencies:
   ```bash
   # Replace with your project's specific install command (e.g., npm install, pip install -r requirements.txt)
   ```

### Configuration
Set up your environment variables or local configuration files to declare your clinic endpoints and database credentials before initiating the project.

## ⚖️ License
This project is open-source. Please check the repository settings for licensing details.
