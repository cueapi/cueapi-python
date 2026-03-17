"""Worker transport — create a cue that uses worker pull instead of webhook."""

from cueapi import CueAPI

client = CueAPI("cue_sk_your_key")

# Create a worker-transport cue (no callback URL needed)
cue = client.cues.create(
    name="local-data-pipeline",
    cron="0 */6 * * *",  # Every 6 hours
    transport="worker",
    payload={"pipeline": "etl", "source": "postgres"},
)
print(f"Worker cue created: {cue.id}")
print(f"Transport: {cue.transport}")
print(f"Next run: {cue.next_run}")

# Your local worker daemon polls for executions:
#   pip install cueapi-worker
#   cue worker start --key cue_sk_your_key
