from dotenv import load_dotenv
from src.nebius_client import NebiusClient

load_dotenv()

def main():
    try:
        client = NebiusClient()
        models = client.client.models.list()
        print("Modelli trovati che contengono 'nemotron' o 'bge':")
        for m in models.data:
            name = m.id.lower()
            if 'nemotron' in name or 'bge' in name:
                print(f"- {m.id}")
                
    except Exception as e:
        print(f"Errore durante il recupero dei modelli: {e}")

if __name__ == "__main__":
    main()
