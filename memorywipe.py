import os
import click

@click.command()
def sanitize():
    """Sanitization command"""
    click.secho("You selected wiping...", fg="magenta")

@click.command()
def extract():
    """Extraction command"""
    click.secho("You selected imaging...", fg="magenta")
    # Add your code here

@click.command()
def verify():
    """Verification command"""
    click.secho("You selected wiping...", fg="magenta")

@click.group()
def main():
    """A linux command line utility for storage sanitization. 
    Developed for IoT devices with shell access, keeping modern flash storages like SSDs in mind.
    
    Main commands:\n
    1) sanitize: Sanitization (Wiping)\n
    2) extract: Extraction (Imaging)\n
    3) verify: Verification (External process
    """
    pass

if __name__ == '__main__':
    main.add_command(sanitize)
    main.add_command(extract)
    main.add_command(verify)
    main()
