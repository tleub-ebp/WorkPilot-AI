# Ce fichier est désormais obsolète : le backend LLM se lance automatiquement via provider_api.py
# Il est conservé temporairement pour compatibilité, mais ne fait qu'appeler provider_api.py
import os
import sys

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("provider_api:app", host="0.0.0.0", port=9000, reload=True)