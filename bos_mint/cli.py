import click


@click.group()
def main():
    pass


@main.command()
@click.option("--port", type=int, default=5000)
@click.option("--host", type=str, default="localhost")
def start(port, host):
    from bos_mint import Config
    from bos_mint.web import app
    app.run(debug=Config.get("debug"), port=port, host=host)


if __name__ == "__main__":
    main()
