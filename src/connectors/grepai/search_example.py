from .client import GrepaiClient

client = GrepaiClient()

# Exemple de recherche avec Grepai
query = "def my_function"
result = client.search(query=query)
print("Résultat de la recherche Grepai:", result)
