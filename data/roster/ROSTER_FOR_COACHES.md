# Beach VB roster spreadsheet — coach instructions

## What this file is

**`roster_new.xlsx`** lists every athlete on the squad and their IDs in each tracking system (GymAware, VALD, Catapult, WHOOP). The analytics team uses it to link data correctly in Power BI.

## How to get the file

Ask your tech contact for the latest copy, or download from the project GitHub repo:

**Path:** `data/roster/roster_new.xlsx`

## What to edit

Use the **GymAware** sheet (do not rename the sheet or delete the header row).

| Column (typical name) | What to enter |
|----------------------|----------------|
| Last Name / First Name | Athlete name |
| GymAware API ID | Number from GymAware (required for every athlete) |
| VALD Profile ID | UUID if they have VALD testing |
| Catapult jersey / athlete ID | Jersey or UUID if used |
| WHOOP user ID | Numeric WHOOP ID once the athlete has connected their band (leave blank until then) |

Leave cells **blank** when a value does not apply (do not type `N/A` unless you prefer — blanks are fine).

## After you save

Send the updated `.xlsx` back to the tech team (SharePoint, email, or GitHub — they will tell you which). You do **not** need any passwords or database access.

## Adding a new player

1. Add a new row with name + GymAware API ID.  
2. Fill other IDs when you have them.  
3. Send the file back. The tech team will assign a **Global Athlete ID** in the system (you can leave that column blank unless they ask you to fill it).
