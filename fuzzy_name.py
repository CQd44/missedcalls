import psycopg2, toml
from rapidfuzz import process, fuzz

CONFIG = toml.load("./config.toml") #load variables from toml file
CONNECT_STR = f'dbname = {CONFIG['credentials']['dbname']} user = {CONFIG['credentials']['username']} password = {CONFIG['credentials']['password']} host = {CONFIG['credentials']['host']}'

def standardize_agents_title_case():
    try:
        conn = psycopg2.connect(CONNECT_STR)
        cur = conn.cursor()

        # 1. Fetch distinct names
        cur.execute("SELECT DISTINCT(agent) FROM qa WHERE agent IS NOT NULL;")
        raw_names = [row[0] for row in cur.fetchall()]
        
        # 2. Pre-process: Clean and Title Case everything for initial grouping
        unique_names = list(set([name.strip().title() for name in raw_names]))
        
        name_mapping = {}
        standardized_set = []

        # 3. Fuzzy match to group similar names
        for name in unique_names:
            match = process.extractOne(name, standardized_set, scorer=fuzz.WRatio, score_cutoff=90)
            
            if match:
                # Store the match found in the standardized_set
                name_mapping[name] = match[0]
            else:
                standardized_set.append(name)
                name_mapping[name] = name

        # 4. Update the database
        print(f"Updating rows with Title Case standardization...")
        
        # We also need to map the original "raw" names to their new title-cased versions
        for raw_name in raw_names:
            standardized_version = name_mapping.get(raw_name.strip().title())
            
            # Only update if the current name in DB is different from standardized version
            if raw_name != standardized_version:
                cur.execute(
                    "UPDATE qa SET agent = %s WHERE agent = %s;",
                    (standardized_version, raw_name)
                )
        
        conn.commit()
        print("Standardization to Title Case complete.")

    except Exception as e:
        print(f"Error: {e}")
        if conn: conn.rollback()
    finally:
        if cur: cur.close()
        if conn: conn.close()

if __name__ == "__main__":
    standardize_agents_title_case()