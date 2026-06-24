import requests
import json
URL = "https://graphql.anilist.co"

QUERY = """
query{
    Media(id:1,type: ANIME){
    title{
    english
    romaji
    }
    genres
    averageScore
    description
            }
                }
"""

response = requests.post(URL,json={"query": QUERY})

data = response.json()

print(json.dumps(data, indent=2))
print(data["data"]["Media"]["title"]["english"])

