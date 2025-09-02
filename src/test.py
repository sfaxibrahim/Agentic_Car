from langchain_community.utilities import SerpAPIWrapper

# Initialize SerpAPI with your key
search = SerpAPIWrapper(serpapi_api_key="4fa4884cf498f97235632e8773157f9454d5e02072f1ec0eef4deb1c0d915ad3")

# Google search
google_results = search.run("latest AI news")

# YouTube search (change engine)
youtube_results = search.run({
    "engine": "youtube",
    "search_query": "laptop repair tutorial"
})

print("Google:", google_results[:200])
print("YouTube:", youtube_results[:200])
