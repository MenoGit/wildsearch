from flask import Flask, render_template, request
from whoosh import index
from index import search_index
from pagerank import load_ranks, rank_results

app = Flask(__name__)
ix = index.open_dir("whoosh_index")
ranks = load_ranks("data/pagerank.json")




@app.route("/")

def home():
    return render_template("index.html") 

@app.route("/search")
def search():
    query = request.args.get("q", "")
    if query == "":
        return "Error: Query is empty" 
    
    total_matches, doc_ids = search_index(ix, query, None, True)
    results = rank_results(doc_ids,ranks,10)
    return f"Found {total_matches} matching pages: {results}"

if __name__ == "__main__":
    app.run(debug=True)


