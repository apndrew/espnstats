import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from espn_api.football import League
import time
import sys

# --- CONFIGURATION --- #
FIREBASE_KEY_PATH = 'serviceAccountKey.json'
APP_ID = 'GLOVILLE-2025-LIVE-FEED'

# ESPN Config
YEAR = 2025
# Note: Week 16 is typical for playoffs, but adjust as needed
CURRENT_WEEK = 15

# League IDs
COLGATE_LEAGUE_ID = 1450464291  # <--- REPLACE (Integers, no quotes)
PALMOLIVE_LEAGUE_ID = 1117490644  # <--- REPLACE (Integers, no quotes)

# Cookies (MANDATORY for Private Leagues)
SWID = "{C98EC394-9BE7-47AE-AC5E-E8BD44C78C66}"  
ESPN_S2 = "AECbsPxOVoookV%2B9ZpIQcJA4mWAbyrEtX9RtisDy1yB97gZFwRRw7d0tnZlvvOMeQF0Nxb7J%2BWWBI%2BFu9lXSL6LmuKINgfmWr5CMTbE6PahzJSbHMQKsHoZGXmDR4NnYk6I600MaP4%2FDEKd4ZQUvJKJSxT960TDgjxcff%2FEzGRCSVm0NUpQLZF3mb2XCd8wSfQ1dIKcfmkV5tmMSc2saXLyWwEqyrKya8J1M%2B60FBstHy2sUii%2Fum3TF6xRrxLkh4NWnPRh1R3GIul3lNxgBk1jv"

# Initialize Firebase
if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY_PATH)
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- NEW FUNCTION TO CLEAR CHAT ---
def clear_chat():
    """Deletes all documents from the leagueChat collection in the current app's public data path."""
    if APP_ID == 'default-app-id':
        print("\n🛑 STOP: APP_ID must be set before clearing chat.")
        return

    print("🗑️ Starting league chat cleanup...")
    
    # Define the collection path based on the structure used in index.html
    chat_collection_ref = db.collection('artifacts').document(APP_ID)\
                             .collection('public').document('data')\
                             .collection('leagueChat')
    
    # To handle large collections, we loop and delete in batches of 500
    deleted_count = 0
    limit = 500
    
    while True:
        docs = chat_collection_ref.limit(limit).stream()
        batch = db.batch()
        batch_count = 0
        
        has_more = False
        for doc in docs:
            batch.delete(doc.reference)
            deleted_count += 1
            batch_count += 1
            has_more = True
            
        if batch_count > 0:
            batch.commit()
            print(f"    -> Deleted batch of {batch_count} documents.")
        
        if not has_more:
            break
            
    if deleted_count > 0:
        print(f"\n✅ Chat cleared successfully. Total deleted: {deleted_count} messages.")
    else:
        print("\nℹ️ Chat collection was already empty.")

# --- NEW FUNCTION TO CLEAR MATCHES ---
def clear_matches():
    """Deletes all documents from the fantasyMatches2025 collection."""
    if APP_ID == 'default-app-id':
        print("\n🛑 STOP: APP_ID must be set before clearing matches.")
        return

    print("🗑️ Starting fantasy match cleanup...")
    
    match_collection_ref = db.collection('artifacts').document(APP_ID)\
                             .collection('public').document('data')\
                             .collection('fantasyMatches2025')
    
    deleted_count = 0
    limit = 500
    
    while True:
        docs = match_collection_ref.limit(limit).stream()
        batch = db.batch()
        batch_count = 0
        
        has_more = False
        for doc in docs:
            batch.delete(doc.reference)
            deleted_count += 1
            batch_count += 1
            has_more = True
            
        if batch_count > 0:
            batch.commit()
            print(f"    -> Deleted batch of {batch_count} documents.")
        
        if not has_more:
            break
            
    if deleted_count > 0:
        print(f"\n✅ Matches cleared successfully. Total deleted: {deleted_count} matches.")
    else:
        print("\nℹ️ Match collection was already empty.")
        
# --- END NEW FUNCTION ---

def get_injury_code(status):
    """Shortens injury status for UI display"""
    status = str(status).upper()
    if status in ['QUESTIONABLE']: return 'Q'
    if status in ['DOUBTFUL']: return 'D'
    if status in ['OUT']: return 'O'
    if status in ['IR', 'INJURED RESERVE']: return 'IR'
    if status in ['PUP']: return 'PUP'
    if status in ['SUSPENDED']: return 'SUS'
    return None # Active or healthy

# --- MODIFIED: Improved logic for game clock display ---
def format_game_clock(player):
    """
    Determines the game status and clock string, ensuring quarter and time are correctly packaged.
    """
    
    if not hasattr(player, 'game_played'):
        return "N/A", "N/A"

    # Game is Final (game_played == 100)
    if player.game_played >= 100:
        return "Final", "Final"
        
    # Game is In Progress (Live: 0 < game_played < 100)
    if player.game_played > 0 and player.game_played < 100:
        # Fetch the game clock and quarter attributes
        # ESPN API uses 'qtr' (integer 1-5 for quarter/OT) and 'game_clock' (string like "5:12" or "Halftime")
        quarter = getattr(player, 'qtr', None)
        clock = getattr(player, 'game_clock', None)
        
        # Determine Quarter Display
        qtr_str = ""
        if quarter == 1: qtr_str = "Q1"
        elif quarter == 2: qtr_str = "Q2"
        elif quarter == 3: qtr_str = "Q3"
        elif quarter == 4: qtr_str = "Q4"
        elif quarter == 5: qtr_str = "OT"
        elif quarter and quarter > 5: qtr_str = f"Q{quarter}"
        else: qtr_str = "In Play" # Default if quarter is missing for a live game

        game_clock_display = ""
        
        if clock and clock.lower() == 'halftime':
            # Specific handling for halftime
            game_clock_display = "Halftime"
        elif clock:
            # If clock has a value (e.g., "5:12"), append "Left" if it's not already there 
            time_remaining = clock.replace(" Left", "").strip()
            if time_remaining:
                 # Ensure quarter is only shown if it's meaningful (not "In Play")
                if qtr_str != "In Play":
                    game_clock_display = f"{qtr_str} - {time_remaining} Left"
                else:
                    game_clock_display = f"{time_remaining} Left"
            else:
                game_clock_display = qtr_str # If clock is an empty string, just show quarter/status
        
        # Final cleanup for states where clock data is minimal
        if not game_clock_display or game_clock_display.strip() == "In Play":
             game_clock_display = "Live" 
             
        return "In Play", game_clock_display
    
    # Game is Pre-Game (game_played == 0)
    if player.game_played == 0 and hasattr(player, 'game_date') and player.game_date:
        # Format the datetime object to Day, Time (e.g., Sun 1:00 PM)
        game_datetime = player.game_date
        # Check if game_date is a datetime object, sometimes it's None for pre-game.
        if game_datetime:
            # For simplicity and robust formatting:
            clock_display = game_datetime.strftime("%a %I:%M %p")
            return "Pre-Game", clock_display
        
    return "Pre-Game", "TBD" # Default fallback for not-yet-scheduled

# --- END MODIFIED SECTION ---

def transform_matchup(matchup, league_name, week_number): # MODIFIED: Added week_number
    # Helper to process a team side
    def build_team(team, lineup, score):
        if not team: return None

        roster = []
        bench = []
        
        # New list to track projected points for players who are NOT finished
        remaining_projected_points = []
        
        # Define reduction factor to lower optimistic projections (Reduced from 0.75 to 0.60)
        PROJECTION_REDUCTION_FACTOR = 0.60
        
        for player in lineup:
            
            # Get updated game status and clock information
            status, clock_display = format_game_clock(player)

            # --- EXTRACT DEEP STATS ---
            raw_injury = getattr(player, 'injuryStatus', 'Active')
            injury_code = get_injury_code(raw_injury)
            
            season_pts = getattr(player, 'total_points', 0.0)
            if season_pts == 0.0 and hasattr(player, 'points'): 
                pass 

            p_data = {
                'id': f"p-{player.playerId}",
                'name': player.name,
                'position': player.slot_position,
                'realPosition': getattr(player, 'position', player.slot_position),
                'score': "{:.2f}".format(player.points),
                'projected': "{:.2f}".format(player.projected_points),
                
                # UPDATED FIELDS
                'status': status, # Will be 'In Play', 'Final', or 'Pre-Game'
                'gameClock': clock_display, # e.g., 'Q3 - 5:12 Left', 'Halftime', 'Sun 1:00 PM', or 'Final'
                
                'opponent': getattr(player, 'proOpponent', "BYE") or "BYE",
                'headshot': f"https://a.espncdn.com/i/headshots/nfl/players/full/{player.playerId}.png",
                
                # Extended Stats
                'proTeam': getattr(player, 'proTeam', 'FA'),
                'injuryStatus': raw_injury,
                'injuryCode': injury_code,
                'totalPoints': "{:.2f}".format(season_pts),
                'percentOwned': "{:.1f}".format(getattr(player, 'percent_owned', 0.0)),
                'percentStarted': "{:.1f}".format(getattr(player, 'percent_started', 0.0)),
                'posRank': getattr(player, 'posRank', 'N/A')
            }

            if player.slot_position in ['BE', 'IR']:
                bench.append(p_data)
            else:
                roster.append(p_data)
                
                # --- NEW LOGIC FOR PROJECTED SCORE ---
                # Only include projected points if the player has NOT played (status is not 'Final')
                # AND apply the reduction factor
                if status != 'Final':
                     remaining_projected_points.append(player.projected_points * PROJECTION_REDUCTION_FACTOR)


        # Totals
        # The projectedScore is now the reduced sum of projections for players who haven't finished.
        total_proj = sum(remaining_projected_points)
        
        return {
            'id': f"m-{team.team_id}",
            'name': team.team_name,
            'rank': team.standing,
            'avatar': team.logo_url,
            'totalScore': "{:.2f}".format(score),
            # Send the remaining projected score to the front end
            'projectedScore': "{:.2f}".format(total_proj),
            'starters': roster,
            'bench': bench,
            'league': league_name
        }

    # Extract Data
    home_data = build_team(matchup.home_team, matchup.home_lineup, matchup.home_score)
    away_data = build_team(matchup.away_team, matchup.away_lineup, matchup.away_score)

    if not home_data or not away_data: return None

    # --- PADDING LOGIC (Kept for consistent data structure) ---
    bench_1 = home_data['bench']
    bench_2 = away_data['bench']
    max_bench = max(len(bench_1), len(bench_2))
    
    def pad_list(player_list, target_len, slot_name="BN"):
        while len(player_list) < target_len:
            player_list.append({
                'id': f"empty-{len(player_list)}",
                'name': "Empty Slot",
                'position': slot_name,
                'realPosition': slot_name,
                'score': "0.00",
                'projected': "0.00",
                'status': "Pre-Game", # Default to Pre-Game for empty slots
                'gameClock': "",
                'opponent': "",
                'headshot': "https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/0.png&w=96&h=70",
                'proTeam': "", 'injuryStatus': "Active", 'injuryCode': None, 'totalPoints': "0", 'percentOwned': "0", 'percentStarted': "0"
            })
        return player_list

    home_data['bench'] = pad_list(bench_1, max_bench)
    away_data['bench'] = pad_list(bench_2, max_bench)

    max_starters = max(len(home_data['starters']), len(away_data['starters']))
    home_data['starters'] = pad_list(home_data['starters'], max_starters, "FLX")
    away_data['starters'] = pad_list(away_data['starters'], max_starters, "FLX")
    
    # --- MODIFIED: Add week number to the ID and the data payload ---
    
    # Generate a unique ID that includes the week number
    match_id = f"{league_name}-{week_number}-{matchup.home_team.team_id}-{matchup.away_team.team_id}"

    return {
        'id': match_id,
        'league': league_name,
        'round': f"Week {week_number}", # Base round label
        'week': week_number,             # NEW FIELD: Week number for filtering
        'status': 'Live', 
        'winner': None,
        'team1': home_data,
        'team2': away_data,
        'timestamp': int(time.time() * 1000)
    }

def sync_league(league_id, league_name, batch, week_number): # MODIFIED SIGNATURE
    if league_id == 0:
        print(f"⚠️ Skipping {league_name} (ID not set in script)")
        return

    print(f"🏈 Connecting to {league_name} ({league_id}) for Week {week_number}...")
    
    try:
        # Note: ESPN's API often returns game data based on EST/EDT.
        league = League(league_id=league_id, year=YEAR, espn_s2=ESPN_S2, swid=SWID)
    except Exception as e:
        print(f"❌ Error connecting to {league_name}: {e}")
        return

    print(f"   ✅ Connected! Fetching Week {week_number} Box Scores...")
    
    try:
        box_scores = league.box_scores(week_number) # Use the passed week_number
    except Exception as e:
        print(f"   ⚠️ Could not fetch scores for Week {week_number}: {e}")
        return
        
    count = 0
    for matchup in box_scores:
        # Pass the week_number to the transformer
        match_data = transform_matchup(matchup, league_name, week_number)
        if match_data:
            # Use the correct Firestore path for the app
            doc_ref = db.collection('artifacts').document(APP_ID)\
                        .collection('public').document('data')\
                        .collection('fantasyMatches2025').document(match_data['id'])
            batch.set(doc_ref, match_data)
            count += 1
            
    print(f"   ✨ Synced {count} Week {week_number} matchups for {league_name}.")

def sync_initial_setup():
    """Initial sync of ALL past weeks (1 through 15)."""
    # Define the range of weeks to fetch (1 to 15)
    # range(1, 16) generates numbers 1, 2, ..., 15
    ALL_WEEKS = range(1, 16)
    
    print(f"Running Initial Setup Sync for Weeks {ALL_WEEKS.start} through {ALL_WEEKS.stop - 1}...")
    
    # We will process in chunks because Firestore batches have a limit (500 ops)
    # Syncing 15 weeks * 2 leagues * ~6 matchups = ~180 writes (well within limit), 
    # but strictly speaking, it's safer to commit per week or just one big batch. 
    # Since it's small enough, one batch is fine.
    
    batch = db.batch()

    for week in ALL_WEEKS:
        sync_league(COLGATE_LEAGUE_ID, 'Colgate', batch, week)
        sync_league(PALMOLIVE_LEAGUE_ID, 'Palmolive', batch, week)

    try:
        batch.commit()
        print('\n✅ Initial Sync Complete (Weeks 1-15).')
    except Exception as e:
        print(f"❌ Firestore Error during initial setup: {e}")

def sync_live_loop():
    """Continuous live sync only for the current week (Week 15)."""
    CURRENT_WEEK_LIVE = 15
    print(f"Running Live Sync for Week {CURRENT_WEEK_LIVE}...")
    batch = db.batch()
    
    sync_league(COLGATE_LEAGUE_ID, 'Colgate', batch, CURRENT_WEEK_LIVE)
    sync_league(PALMOLIVE_LEAGUE_ID, 'Palmolive', batch, CURRENT_WEEK_LIVE)

    try:
        batch.commit()
        print(f'\n✅ Live Sync Complete. Dashboard updated for Week {CURRENT_WEEK_LIVE}.')
    except Exception as e:
        print(f"❌ Firestore Error during live loop: {e}")

if __name__ == '__main__':
    # --- Check for arguments to clear chat ---
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'clear-chat':
        clear_chat()
        sys.exit(0)
    
    # --- Check for arguments to clear matches ---
    if len(sys.argv) > 1 and sys.argv[1].lower() == 'clear-matches':
        clear_matches()
        sys.exit(0)
    
    if APP_ID == 'default-app-id':
        print("\n🛑 STOP: You haven't updated the APP_ID on line 12!")
        print("   1. Go to your website preview.")
        print("   2. Copy the ID from the Blue Box.")
        print("   3. Paste that ID into the script.")
        print("   4. Re-run: 'python sync_espn.py clear-matches' to start fresh.")
        sys.exit(1)
        
    print("--------------------------------------------------")
    print("🏈 Live Fantasy Sync Started")
    print("Run with 'python sync_espn.py clear-chat' to wipe the chat history.")
    print("Run with 'python sync_espn.py clear-matches' to wipe all match data.")
    print("--------------------------------------------------")
    
    # 1. Run initial setup once to ensure all necessary weeks are in the database
    sync_initial_setup()
    
    # 2. Enter continuous live loop for the current week only
    try:
        while True:
            sync_live_loop()
            print("⏳ Waiting 30 seconds for next update...")
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n\n🛑 Script stopped by user.")
        sys.exit(0)
