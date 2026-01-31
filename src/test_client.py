from client import get_client

client = get_client()
athlete = client.get_athlete()
print(athlete.firstname)
