import os
import sys
import urllib.parse

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from rich.console import Console
from rich.prompt import Prompt

# Adiciona o diretório raiz do projeto ao path do Python
# para que possamos importar o módulo de configuração da aplicação.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

try:
    from app.infrastructure.config.config import settings
except ImportError:
    print(
        "Erro: Não foi possível importar as configurações. "
        "Certifique-se de que o script está na pasta 'scripts' na raiz do projeto."
    )
    sys.exit(1)


def clean_mongo_collections():
    """
    Conecta-se ao MongoDB e limpa documentos de coleções específicas
    após a confirmação do usuário.
    """
    console = Console()

    collections_to_clean = ["checkpoints", "checkpoint_writes"]

    console.print(
        "[bold yellow]ATENÇÃO: Este script irá apagar TODOS os documentos das seguintes coleções![/bold yellow]"
    )
    console.print(f"Banco de Dados: [cyan]{settings.MONGODB_DB_NAME}[/cyan]")
    for collection in collections_to_clean:
        console.print(f"  - Coleção: [cyan]{collection}[/cyan]")
    console.print("[bold yellow]Esta operação não pode ser desfeita.[/bold yellow]\n")

    confirmation = Prompt.ask(
        "Digite '[bold green]sim[/bold green]' para continuar", default="não"
    )

    if confirmation.lower() != "sim":
        console.print("[red]Operação cancelada.[/red]")
        return

    try:
        console.print("\nConectando ao MongoDB...", style="italic")
        with MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000) as client:
            client.admin.command("ping")  # Testa a conexão
            db = client[settings.MONGODB_DB_NAME]
            console.print("✅ Conexão estabelecida com sucesso!\n", style="green")

            for collection_name in collections_to_clean:
                collection = db[collection_name]
                try:
                    count_before = collection.count_documents({})
                    if count_before == 0:
                        console.print(
                            f"A coleção '[cyan]{collection_name}[/cyan]' já está vazia."
                        )
                        continue

                    console.print(
                        f"Limpando {count_before} documento(s) da coleção '[cyan]{collection_name}[/cyan]'..."
                    )

                    result = collection.delete_many({})

                    console.print(
                        f"✅ Sucesso! {result.deleted_count} documentos foram removidos.",
                        style="bold green",
                    )
                except Exception as e:
                    console.print(
                        f"⚠️  Aviso: Não foi possível limpar a coleção '{collection_name}'. Pode ser que ela ainda não exista. Erro: {e}"
                    )

    except PyMongoError as e:
        console.print(f"❌ Erro de conexão com o MongoDB: {e}", style="bold red")
    except Exception as e:
        console.print(f"❌ Ocorreu um erro inesperado: {e}", style="bold red")

    console.print("\nScript finalizado.")


if __name__ == "__main__":
    clean_mongo_collections()
