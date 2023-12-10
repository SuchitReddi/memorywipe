import os
import click
import subprocess
from shutil import which as swhich


def check_install(app):
    return swhich(app) is not None
    
class Sanitization:
    def __init__(self, val):
        self.method_value = val
        
    def crypt_wipe(self):
        click.secho("You selected Cryptographic Wipe.", fg="magenta")
        click.echo("Starting Cryptographic Wipe using VeraCrypt...\n")
        try:
            assert self._install_veracrypt()
        except AssertionError:
            raise click.Abort
        list_partitions()
        click.echo("\nIf you want to extract the whole drive, partitioned as sda1, sda2, ..., sdaN; select /dev/sda")
        self.partition = click.prompt("Enter your device's partition (/dev/sda)")
        if not self._check_mount():
            raise click.Abort
        self._veracrypt_encrypt()
        self._wipe_disk()
        self._mount_disk()
        click.echo("Cryptographic Wipe procedure completed successfully!", fg="bright_green")
        
    
    def chk_encrypted(self):
        try:
            lsblk = subprocess.run(["lsblk", "-f", "/dev/nvme0n1p8"], capture_output=True, check=True)
            try:
                output = subprocess.run(["grep", "-q", "veracrypt"], input=lsblk.stdout, check=True)
            except subprocess.CalledProcessError:
                return False
        except subprocess.CalledProcessError:
            click.echo(f"{self.partition} doesn't exist")
            return False
        return True
            
    def _veracrypt_encrypt(self):
        if self.chk_encrypted():
            click.echo("Selected partition is already encrypted! Skipping encryption...\n")
        else:
            q2 = click.prompt("Do you want to encrypt manually or automatically?", type=click.Choice(["m", "a"]), show_choices=True, default="a")
            if q2 == "m":
                click.echo("Starting veracrypt manually...\n")
                out = subprocess.run(["sudo", "veracrypt", "-t", "-c"], capture_output=True)
            elif q2 == "a":
                click.echo("Uses AES, with SHA-512 and makes an NTFS filesystem")
                click.echo("\nEnter strong password for encrypting. (You don't have to remember it)")
                strongp = click.prompt("So set a random password with special characters: ", hide_input=True, confirmation_prompt=True)
                out = subprocess.run(["sudo", "veracrypt", "-t", "-c", -"-volume-type=normal", 
                                f"{self.partition}", "--encryption=aes" "--hash=sha-512", 
                                "--filesystem=ntfs", "-p" f"{strongp}", "--pim=0", 
                                "-k", '""', "--random-source=/dev/urandom"], capture_output=True)
                click.secho(f"Finished encrypting {self.partition}\n", fg="green")
                           
    def _wipe_disk(self):
        click.echo(f"Wiping {self.partition}...")
        if not self._check_mount():
            click.secho("Make sure the disk is unmounted!", fg="red")
            raise click.Abort
        else:
            subprocess.run(["sudo", "dd", "if=/dev/random", f"of={self.partition}", "bs=1M", "status=progress"])
            subprocess.run(["sudo", "dd", "if=/dev/zero", f"of={self.partition}", "bs=1M", "status=progress"])
            
            click.secho(f"{self.partition} overwritten with one write each of random data and zeroes", fg="bright_white")
            self.name = click.prompt("Set device name")
            subprocess.run("sudo", "mkfs.ntfs", "-L", f"{self.name}", f"{self.partition}")
            click.secho(f"Wiped {self.partition}\n", fg="green")
            
    def _mount_disk(self):
        #read -p "Set mounting folder name: " name
        click.echo(f"Mounting {self.partition} at /media/{self.name}")
        subprocess.run(["sudo", "mkdir", f"/media/{self.name}"])
    
        subprocess.run(["sudo", "mount", f"{self.partition}", f"/media/{self.name}/"])
        click.echo("Finished mounting!\n", fg="green") 
                     
    def _check_mount(self):
        try:
            click.echo("Unmounting the partition...")
            # Run the grep command to check if the partition is in /proc/mounts
            try:         
                subprocess.run(["grep", "-qs", self.partition, "/proc/mounts"], check=True)
                # If the above command doesn't raise a CalledProcessError, the partition is mounted
                # Unmount the partition
            except subprocess.CalledProcessError:
                click.secho(f"{self.partition} is already dismounted or doesn't exist")
                return True
            subprocess.run(["sudo", "unmount", self.partition], check=True)
            # Check if the partition is still mounted
            subprocess.run(["grep", "-qs", self.partition, "/proc/mounts"], check=True)
            click.echo(f"Error: Failed to unmount {self.partition}. Please unmount manually.", fg="red")
            return False
        except subprocess.CalledProcessError:
            click.secho(f"{self.partition} has been succesfully mounted")
            return True
        
    def _install_veracrypt(self):
        app="veracrypt"
        click.echo(f"Checking for existing {app} installation...")
        if check_install(app):
            click.echo("Check complete...")
            return True
        
        click.echo("Installing VeraCrypt...")
        veracrypt_url = "https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-console-1.26.7-Debian-11-armhf.deb"
        subprocess.run(["sudo", "wget", veracrypt_url, "--connect-timeout=5", "-c", "-P", "./veracrypt"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        subprocess.run([
        "sudo", "apt", "install", "./veracrypt/veracrypt-console-1.26.7-Debian-11-armhf.deb", "-y"], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        click.echo("Checking for successful installation...")
        if check_install(app):
            click.secho("Check complete. Installed successfully!", fg="bright_green")
            return True
        click.secho("Veracrypt installation failed!! Installation manually.\n", fg="bright_red")    
        click.echo("NOTE: If it did not work for you, change the version and architecture according to your device and os..")
        click.echo("For example, raspberry pi uses armhf architecture. So, the change amd64 to armhf command is:")
        click.echo("sudo wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-console-1.26.7-Debian-11-amd64.deb --connect-timeout=5 -c -P ./veracrypt && sudo apt install ./veracrypt/veracrypt-console-1.26.7-Debian-11-amd64.deb -y")
        return False
                                       
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
