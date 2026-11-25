from flask import Flask, render_template, request
from whoosh import index
from index import search_pagerank, build_doc_mapping
from pagerank import load_ranks
from time import perf_counter

app = Flask(__name__)
ix = index.open_dir("whoosh_index")
ranks = load_ranks("data/pagerank.json")
mapping = build_doc_mapping(ix)




@app.route("/")

def home():
    return render_template("index.html") 

@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if query == "":
        return "Error: Query is empty", 400 
    start = perf_counter()

    total_matches, results = search_pagerank(ix, query, ranks, mapping, 10)

    elapsed = perf_counter() - start
    for url, score in results:
        print(f"{url}, {score}")
    print(f"\nSearch time: {elapsed:.4f} seconds")


    return f"Found {total_matches} matching pages: {results}"

if __name__ == "__main__":
    app.run(debug=True)


