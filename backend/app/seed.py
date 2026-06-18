import sys

from . import supabase_api
from .importer import import_csv
from .supabase_importer import import_csv_supabase


def main():
    if len(sys.argv) < 2:
        print("Informe o caminho do CSV.")
        raise SystemExit(1)
    if supabase_api.enabled():
        result = import_csv_supabase(sys.argv[1], replace=True)
    else:
        result = import_csv(sys.argv[1], replace=True)
    print(result)


if __name__ == "__main__":
    main()
