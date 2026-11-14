import csv
import json

def load_graph(urls_file, edge_file):
    with open(urls_file, "r", encoding="utf-8") as file:
        urls = json.load(file)

    n = len(urls)

    outgoing = [set() for _ in range(n)]

    with open(edge_file, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            source = int(row["source_id"])
            destination = int(row["destination_id"])

            if 0 <= source < n and 0 <= destination < n:
                outgoing[source].add(destination)

    return outgoing

def pagerank(graph, damping=0.9, iterations=100, tolerance=0.000001):
    n = len(graph)

    if n == 0:
        return []

    ranks = [1.0 / n] * n

    for iteration in range(iterations):
        dangling_sum = 0
        for i in range(n):
            if len(graph[i]) == 0:
                dangling_sum += ranks[i]

        base = ((1 - damping) / n) + (damping * dangling_sum / n)
        new_ranks = [base] * n

        for source, destinations in enumerate(graph):
            if not destinations:
                continue

            contribution = damping * ranks[source] / len(destinations)

            for destination in destinations:
                new_ranks[destination] += contribution

        difference = 0
        for i in range(n):
            difference += abs(new_ranks[i] - ranks[i])

        ranks = new_ranks


        print(
            "Iteration", iteration + 1,
            "- Total rank:", round(sum(ranks), 8),
            "changes:", difference
        )
        if difference < tolerance:
            print("PageRank converged")
            break
    return ranks

def show_top_pages(ranks, urls_file, count = 10):
    with open(urls_file, "r", encoding="utf-8") as file:
        urls = json.load(file)
    page_ids = list(range(len(ranks)))

    page_ids.sort(key=lambda i: ranks[i], reverse=True)

    print("\nTop", count, "pages by PageRank:")

    for i in page_ids[:count]:
        print("Page ID:", i)
        print("PageRank:", ranks[i])
        print("URL:", urls[i])
        print()


def save_ranks(ranks, output_file):
    with open(output_file, "w", encoding="utf-8") as file:
        json.dump(ranks, file)

    print("PageRank saved to:", output_file)

if __name__ == "__main__":
    graph = load_graph("data/urls.json", "edges.csv")

    print("Documents:", len(graph))
    print("Unique edges:", sum(len(links) for links in graph))
    print("Dangling pages:", sum(len(links) == 0 for links in graph))

    ranks = pagerank(graph)

    print("Final rank sum:", sum(ranks))
    print("Highest PageRank:", max(ranks))
    print("Lowest PageRank:", min(ranks))

    show_top_pages(ranks, "data/urls.json")
    save_ranks(ranks, "data/pagerank.json")
