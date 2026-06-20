import typer
import copier
import pathlib

app = typer.Typer()
APP_DIR = pathlib.Path(__file__).parent


@app.command()
def main(name: str):
    print(f"Hello {name}")


if __name__ == "__main__":
    app()