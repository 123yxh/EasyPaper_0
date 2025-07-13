import os
import pandas as pd
import matplotlib.pyplot as plt
from langchain_community.utilities.google_scholar import GoogleScholarAPIWrapper
from langchain_community.tools.google_scholar import GoogleScholarQueryRun

def batch_search(queries, wrapper):
    all_results = []
    for query in queries:
        results = wrapper.run(query)
        print(results)
        all_results.extend(results)
    return all_results

wrapper = GoogleScholarAPIWrapper(serp_api_key='d945...', google_scholar_engine='http://api.wlai.vip')
queries = ["Hierarchical Federated Learning"]
results = batch_search(queries, wrapper)
print(results)