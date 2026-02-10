from client import GrepaiClient

if __name__ == "__main__":
    client = GrepaiClient()
    query = "def my_function"
    print(f"Recherche Grepai pour : {query}")
    result = client.search(query=query)
    if 'error' in result:
        print("Erreur lors de la requête Grepai :", result['error'])
    else:
        print("Résultat Grepai :", result)
