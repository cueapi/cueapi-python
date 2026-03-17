"""Basic CueAPI usage — create, list, update, and delete cues."""

from cueapi import CueAPI

client = CueAPI("cue_sk_your_key")

# Create a recurring cue that fires every morning at 9am PT
cue = client.cues.create(
    name="morning-analytics",
    cron="0 9 * * *",
    timezone="America/Los_Angeles",
    callback="https://my-agent.com/webhook",
    payload={"task": "run_analytics"},
    retry={"max_attempts": 3, "backoff_minutes": [1, 5, 15]},
    on_failure={"email": True, "pause": False},
)
print(f"Created: {cue.id} — next run: {cue.next_run}")

# Create a one-time cue
report_cue = client.cues.create(
    name="send-q1-report",
    at="2026-04-01T09:00:00Z",
    callback="https://my-agent.com/webhook",
    payload={"report_id": "q1-2026"},
)
print(f"One-time cue: {report_cue.id}")

# List all cues
cue_list = client.cues.list()
print(f"Total cues: {cue_list.total}")
for c in cue_list.cues:
    print(f"  {c.id} | {c.name} | {c.status} | next: {c.next_run}")

# Get a single cue
fetched = client.cues.get(cue.id)
print(f"Fetched: {fetched.name} — {fetched.schedule.cron}")

# Update a cue
updated = client.cues.update(cue.id, name="updated-analytics", cron="0 10 * * *")
print(f"Updated: {updated.name} — {updated.schedule.cron}")

# Pause and resume
client.cues.pause(cue.id)
print("Paused")

client.cues.resume(cue.id)
print("Resumed")

# Delete
client.cues.delete(cue.id)
client.cues.delete(report_cue.id)
print("Deleted")
