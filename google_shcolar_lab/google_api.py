from serpapi.google_search import GoogleSearch

params = {
  "engine": "google_scholar",
  "q": "Hierarchical Federated Learning",
  "api_key": "d9456a..."
}

search = GoogleSearch(params)
results = search.get_dict()
organic_results = results["organic_results"]
print(organic_results)