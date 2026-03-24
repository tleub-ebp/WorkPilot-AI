import argparse

from services.provider_registry import get_provider_status

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gestion des providers LLM disponibles."
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="Lister les providers LLM disponibles",
    )
    args = parser.parse_args()

    if args.list_providers:
        print("Providers LLM disponibles :")
        for name, status in get_provider_status().items():
            print(f"- {name}: {'OK' if status else 'Non configuré'}")
    else:
        parser.print_help()
