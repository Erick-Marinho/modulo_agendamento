import os
import re
import sys
import urllib.parse
from urllib.parse import quote_plus

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


def escape_mongodb_uri(uri: str) -> str:
    """
    Corrige a URI do MongoDB aplicando URL encoding adequado
    ao nome de usuário e senha conforme RFC 3986.
    Utiliza regex para extrair corretamente as credenciais, mesmo
    quando a senha contém caracteres especiais como '@'.
    """
    try:
        # Padrão regex para extrair componentes da URI do MongoDB
        # mongodb://[username:password@]host[:port][/database][?options]
        pattern = (
            r"^mongodb://(?:([^:@]+):([^@]+)@)?([^:/?]+)(?::(\d+))?(/[^?]*)?(?:\?(.*))?$"
        )

        match = re.match(pattern, uri)
        if not match:
            console = Console()
            console.print(
                "⚠️  URI do MongoDB não reconhecida, usando formato original",
                style="yellow",
            )
            return uri

        username, password, hostname, port, path, query = match.groups()

        # Se não há credenciais, retorna a URI original
        if not username:
            return uri

        # Aplica URL encoding nas credenciais
        escaped_username = quote_plus(username)
        escaped_password = quote_plus(password) if password else ""

        # Reconstrói a URI com as credenciais escapadas
        if escaped_password:
            auth_part = f"{escaped_username}:{escaped_password}@"
        else:
            auth_part = f"{escaped_username}@"

        # Reconstrói a URI completa
        escaped_uri = f"mongodb://{auth_part}{hostname}"

        if port:
            escaped_uri += f":{port}"

        if path:
            escaped_uri += path
        else:
            escaped_uri += "/"  # Adiciona '/' se não há path

        if query:
            escaped_uri += f"?{query}"

        return escaped_uri

    except Exception as e:
        console = Console()
        console.print(f"❌ Erro ao processar URI do MongoDB: {e}", style="bold red")
        console.print("Usando URI original (pode causar problemas de conexão)")
        return uri


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

        # Aplica escape adequado na URI do MongoDB
        escaped_uri = escape_mongodb_uri(settings.MONGODB_URI)

        # Mostra versão mascarada da URI para debug (ocultando credenciais)
        masked_uri = re.sub(r"://[^@]+@", "://***:***@", escaped_uri)
        console.print(f"URI processada: {masked_uri}", style="dim")

        with MongoClient(escaped_uri, serverSelectionTimeoutMS=5000) as client:
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
