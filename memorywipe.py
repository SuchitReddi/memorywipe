import os
import click


class Sanitization:
    def __init__(self, val):
        self.method_value = val
        
    def crypt_wipe(self):
        click.echo(self.method_value)
        pass
    
    def ata_hdparm(self):
        click.echo(self.method_value)
        pass

    
    def auto_wipe(self):
        click.echo(self.method_value)
        pass
    

def validate_sanitize(ctx, param, value):
    if not value or ctx.resilient_parsing:
        click.secho("You selected wiping...", fg="magenta")
        click.echo("""
            Available Methods: [Default: 5]
            [1] Cryptographic Wipe
            [2] ATA Secure Erase (hdparm)
            [3] SATA Secure Erase (sg-utils)
            [4] NVMe Secure Erase (nvme-cli)
            [5] Automatic wipe (Executes the best compatible method)
            """)
        value = click.prompt("Select the wiping method", type=int)
        try:
            assert value in range(1, 6)
            return value
        except AssertionError as e:
            raise click.BadParameter("Invalid value range. Must be between 1 and 5") 
    return value

@click.command()
@click.option("--method", "-m", type=click.IntRange(1, 6), callback=validate_sanitize, is_eager=True)
def sanitize(method):
    """Sanitization command"""
    wipe = Sanitization(method)
    match method:
        case 1:
            wipe.crypt_wipe()
        case 2: 
            wipe.ata_hdparm()
        case 3 | 4:
            click.echo("No NVMe devices are availble for testing. Will be added soon...")
        case 5:
            wipe.auto_wipe()
        case _:
            click.echo("Wrong input value")
    
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
