import os
import click
import subprocess


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


def list_partitions():
    valid_input = False
    while True:
        q1 = click.prompt("Do you want to see all the partitions?(y/n)[n]")
        if q1 == "y":
            valid_input = True
            break
        elif q1 == "n" or q1 == "":
            break
        else:
            print("Invalid input. Please give either 'y' or 'n'")
            print()

    if valid_input:
        app = "lsblk"
        try:
            # Check if 'lsblk' is installed
            subprocess.check_call(["which", app])
            # If 'lsblk' is installed, use it to list the partitions
            subprocess.run([app, "-f"])
        except subprocess.CalledProcessError:
            # If 'lsblk' is not installed, use 'df -hT' as a fallback
            subprocess.run(["df", "-hT"])
    

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

def validate_extract(ctx, param, value):
    if not value or ctx.resilient_parsing:
        click.secho("You selected imaging...", fg="magenta")
        click.echo("Select a partition to extract:-")
        list_partitions()
        click.echo("If you want to extract the whole drive, partitioned as sda1, sda2, ..., sdaN; select /dev/sda")
        value = click.prompt("Enter your device's partition (/dev/sda)")
    try:
        subprocess.run(["grep", "-qs", value, "/proc/mounts"], check=True)
    # If the above command doesn't raise a CalledProcessError, the partition exists
        return value
    except subprocess.CalledProcessError:
    # The partition doesn't exist, print message and return False
        click.echo("\nYour partition does not exist. Enter the correct partition. Starting again...\n")
        ctx.abort()


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
@click.option("--partition", "-p", type=click.Path(exists=True, readable=False, resolve_path=True), callback=validate_extract, is_eager=True)
@click.option("--bytesize", "-b", default="1M", help="""
                N and BYTES may be followed by the following multiplicative suffixes:
                c =1, w =2, b =512, kB =1000, K =1024, MB =1000*1000, M =1024*1024, xM =M,
                GB =1000*1000*1000, G =1024*1024*1024, and so on for T, P, E, Z, Y.
                """)
def extract(partition, bytesize):
    """Extraction command"""
    loc = click.prompt("Enter ouput location for the bin file (/path/to/your/image.bin)")
    subprocess.run(["sudo", "dd", f"if={partition}", f"of={loc}", f"bs={bytesize}", "status=progress"])

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
