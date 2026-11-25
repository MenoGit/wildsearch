"""
index using BM25
Run with:  python3 index.py
"""

import os
import json
import sys

from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import QueryParser, OrGroup, AndGroup
from whoosh.filedb.filestore import FileStorage

PAGES_DIR = "wildsearch-dataset/data/pages"
INDEX_DIR = "whoosh_index"

#settings

def get_schema():
    "schema off the things the crawler collected"
    return Schema(
        id=ID(stored=True, unique=True),
        url=ID(stored=True),
        text=TEXT(stored=True)
    )


def check_index(index_dir):
    return os.path.exists(index_dir) and exists_in(index_dir)


def initialize_index(index_dir, schema):
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
    storage = FileStorage(index_dir)
    return storage.create_index(schema)


def get_index(index_dir):
    return open_dir(index_dir)


def configure_query_parser(index_instance, conjunctive=True):
    #and/or
    group_mode = AndGroup if conjunctive else OrGroup
    return QueryParser("text", index_instance.schema, group=group_mode)


def write_documents_to_index(ix, pages_dir):
    if not os.path.exists(pages_dir) and os.path.exists("data/pages"):
        pages_dir = "data/pages"

    if not os.path.exists(pages_dir):
        print(f"Error: '{pages_dir}' directory not found ")
        print("Check if dataset is in /wildsearch")
        sys.exit(1)

    file_list = [f for f in os.listdir(pages_dir) if f.endswith(".json") and not f.startswith("._")]
    print(f"Indexing {len(file_list)} files from '{pages_dir}'")

    with ix.writer(procs=1, limitmb=256) as writer:
        for file_name in file_list:
            file_path = os.path.join(pages_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    writer.add_document(
                        id=str(data["id"]),
                        url=data["url"],
                        text=data["text"]
                    )
            except Exception as e:
                print(f"Warning: Failed to parse file {file_name}. Reason: {e}")

def build_doc_mapping(ix):
    mapping = {}

    with ix.searcher() as searcher:
        for docnum in searcher.reader().all_doc_ids():
            fields = searcher.stored_fields(docnum)
            mapping[docnum] = int(fields["id"])
    return mapping

def search_pagerank(ix, query_str, ranks, mapping, limit=10):

    parser = configure_query_parser(ix, conjunctive=True)
    parsed_query = parser.parse(query_str)

    with ix.searcher() as searcher:

        matching_docs = searcher.docs_for_query(parsed_query)
        results = []

        for docnum in matching_docs:
            crawler_id = mapping[docnum]
            score = ranks[crawler_id];
            results.append((docnum, score))

        total_matches = len(results)

        results.sort(key=lambda x: x[1], reverse=True)

        top_docs = results[:limit]
        top_results = []
        for docnum, score in top_docs:
            url = searcher.stored_fields(docnum)["url"]
            top_results.append((url,score))
        return total_matches, top_results 



def search_index(ix, query_str, limit, conjunctive, option="All"):
    parser = configure_query_parser(ix, conjunctive=conjunctive)
    parsed_query = parser.parse(query_str)
    
    with ix.searcher() as searcher:
        results = searcher.search(parsed_query, limit=limit)
        total_matches = len(results)
        hits_list = [{"id":hit["id"], "url": hit["url"]} for hit in results]
        return total_matches, hits_list



def index_documents(pages_dir, index_dir):
    schema = get_schema()
    ix = initialize_index(index_dir, schema)
    write_documents_to_index(ix, pages_dir)
    print(f"Inverted index is ready '{index_dir}'.")


def execute_search(index_dir, query_str, limit=10, conjunctive=True):
    if not check_index(index_dir):
        print(f"Error: Inverted index not found at '{index_dir}'")
        return

    ix = get_index(index_dir)
    total_matches, hits = search_index(ix, query_str, limit, conjunctive)
    
    print(f"\n________ Found {total_matches} total matches (Showing Top {limit}) ________")
    if not hits:
        print("No matching tuples found.")
        return

    for idx, hit in enumerate(hits, start=1):
        print(f"[{idx}] DocID: {hit['id']} | URL: {hit['url']}")


def query_session():
    limit = 10
    conjunctive = True

    while True:
        mode_str = "CONJUNCTIVE (AND)" if conjunctive else "DISJUNCTIVE (OR)"
        print(f"\nCurrent Limit: {limit} | Mode: {mode_str}")
        print("Commands: 1. !limit <int> | 2. !mode and/or | 3. !exit")
        
        try:
            user_input = input("Enter query or command: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting")
            break

        if not user_input:
            continue

        if user_input.startswith("!"):
            parts = user_input.split()
            cmd = parts[0].lower()
            
            if cmd == "!exit":
                print("Exiting")
                break
                
            elif cmd == "!limit" and len(parts) > 1:
                try:
                    limit = int(parts[1])
                    print(f"limit set to: {limit}")
                except ValueError:
                    print("Error: must be an integer.")
                    
            elif cmd == "!mode" and len(parts) > 1:
                arg = parts[1].lower()
                if arg == "and":
                    conjunctive = True
                    print("Changed mode to: CONJUNCTIVE (AND)")
                elif arg == "or":
                    conjunctive = False
                    print("Changed mode to: DISJUNCTIVE (OR)")
                else:
                    print("Error: type either 'and' or 'or'.")
            else:
                print("Error: Unknown command.")
            continue

        execute_search(INDEX_DIR, user_input, limit=limit, conjunctive=conjunctive)


def main():
    index_documents(PAGES_DIR, INDEX_DIR)
    query_session()


if __name__ == "__main__":
    main()
