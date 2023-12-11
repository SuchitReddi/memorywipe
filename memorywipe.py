import os
import click
import subprocess
from shutil import which as swhich


def check_install(app):
    return swhich(app) is not None

def list_partitions():
    valid_input = False
    q1 = click.prompt("Do you want to see all the partitions?", type=click.Choice(["y", "n"]), default="n")
    if q1 == "y":
        valid_input = True
        
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
            
            
def validate_partition(path):
    try:
        subprocess.run(["grep", "-qs", path, "/proc/mounts"], check=True)
        # If the above command doesn't raise a CalledProcessError, the partition exists
        return path
    except subprocess.CalledProcessError:
        # The partition doesn't exist, print message and return False
        click.echo("\nYour partition does not exist. Enter the correct partition. Start again...\n")
        return False
    
    
        
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
        click.secho("WARNING: This process is irreversible. Create necessary backups if required (You may use the extraction module for this).\n", fg="yellow")
        click.secho("NOTE: Cryptographic Wipe on Flash Storage partitions may not be effective. Perform it on the whole disk.", fg="blue")
        click.secho("If there are multiple partitions in the device, format them into one single partition, and then wipe it.", fg="blue")
        list_partitions()
        click.echo("\nIf you want to wipe the whole drive, partitioned as sda1, sda2, ..., sdaN; select /dev/sda")
        self.partition = click.prompt("Enter your device's partition", default="/dev/sda")
        if not validate_partition(self.partition):
            raise click.Abort
        if not self._check_mount():
            raise click.Abort
        self._veracrypt_encrypt()
        self._wipe_disk()
        self._mount_disk()
        click.echo("Cryptographic Wipe procedure completed successfully!", fg="bright_green")
        del self.partition
        
    
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
        del self.name
                     
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
        click.secho("You selected ATA Secure Erase...", fg="magenta")
        click.echo("Starting ATA Secure Erase using hdparm...")
        try:
            assert self._install_tool("hdparm")
        except AssertionError:
            raise click.Abort
        
        list_partitions()
        click.echo("\nIf you want to wipe the whole drive, partitioned as sda1, sda2, ..., sdaN; select /dev/sda")
        self.partition = click.prompt("Enter your device's partition", default="/dev/sda")
        if not validate_partition(self.partition):
            raise click.Abort
        
        self._chk_compat_hdparm()
        self._chk_freeze()
        click.echo("The time taken for this process to finish will be:")
        try:
            info = subprocess.run(["sudo", "hdparm", "-I", f"{self.partition}"], capture_output=True)
            output = subprocess.run(["grep", "-i", '"erase unit"'], input=info.stdout, check=True)
        except subprocess.CalledProcessError:
            click.secho("Couldn't get the partition information.\n", fg="yellow")
        self._pass_hdparm = click.prompt("Set a password", hide_input=True, confirmation_prompt=True)
        # subprocess.run(["sudo" "hdparm" "--user-master" "u" "--security-set-pass" f"{self._pass_hdparm}" f"{self.partition}"])
        click.echo("Password set!\n")
        self._select_enhance()
        click.echo("\nATA Secure Erase procedure successfully completed!", fg="bright_green")
        del self.partition
        del self._pass_hdparm
        
    def _install_tool(self, app):
        click.echo(f"\nChecking existing installation for {app}")
        if check_install(app):
            click.echo("Check complete...")
        else:
            if app == "nandump":
                app = "mtd-utils"
            click.echo(f"Installing {app}...")
            try:
                subprocess.run(["sudo", "apt-get", "install", app, "-y"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except subprocess.CalledProcessError:
                click.secho(f"Error: Unable to install {app}. Please install it manually.", fg="red")
                raise click.Abort
    
    def _chk_compat_hdparm(self):
        try:
            info = subprocess.run(["sudo", "hdparm", "-I", f"{self.partition}"], capture_output=True)
            output = subprocess.run(["grep", "-i", '"sanitize feature"'], input=info.stdout, check=True)
            click.echo("Your device supports hdparm set!")
        except subprocess.CalledProcessError:
            click.secho("Your device does not support hdaparm set!\n", fg="yellow")
            click.Abort
            
    def _chk_freeze(self):
        hdparm_output = subprocess.check_output(["sudo", "hdparm", "-I", f"{self.partition}"], text=True)
        if "frozen" not in hdparm_output:
            click.echo("Device is not frozen! Continuing to next step...")
        else:
            click.secho("Device is frozen!", fg="yellow")
            click.echo("A system suspend will suspend the device and start it after a minute unfrozen")
            click.secho("YOUR DEVICE WILL TURN OFF FOR A FEW MINUTES IF YOU SELECT YES. DO NOT PANIC\n")
            suspend = click.prompt("Do you want to suspend your system?", type=click.Choice(["y", "n"]), default=True)
            if suspend == "y":
                subprocess.run(["sudo", "systemctl", "suspend"])
            else:
                click.echo("You can't continue with this process without suspending...")
                click.Abort
                
    def _chk_sanitize_status(self):
        hdparm_output= subprocess.check_output(["sudo", "hdparm", "--sanitize-status", f"{self.partition}"], text=True)
        if "sanitize feature" not in hdparm_output:
            click.secho("Your device does not support sanitize feature set!", fg="yellow")
        else:
            click.echo("Your device supports sanitize feature set!")
    
    def _select_enhance(self):
        menu = """
        Available actions: 
        [1] Enhanced Security Erase (Deletes data from bad blocks)
        [2] Security Erase (Does not delete data from bad blocks)
        [3] Sanitize Block Erase
        [4] Sanitize Crypto Scramble (For Self-Encrypting SSDs)
        """
        click.echo(menu)
        erase = click.prompt("Select your erase method", type=click.IntRange(1, 4), show_choices=True)
        match erase:
            case 1:
                click.secho("You selected Enhanced Security Erase", fg="magenta")
                click.echo("This mode writes predetermined data patterns set by the manufacturer to all areas including bad blocks")
                click.echo("Please wait... this may take a long time. Atleast:")
                hdparm = subprocess.run(["sudo", "hdparm", "-I", f"{self.partition}"], capture_output=True)
                subprocess.check_output(["grep", "-i", "erase unit"], input=hdparm.stdout)
                # subprocess.run(["sudo", "hdparm", "--user-master", "u", "--security-erase-enhanced", f"{self._pass_hdparm}", f"{self.partition}"])
                click.echo("Successfully finished Enhanced Security Erase!")
            case 2:
                click.secho("You selected Security Erase", fg="magenta")
                click.echo("This mode writes all user data excluding bad blocks with zeroes")
                click.echo("Please wait... this may take a long time. Atleast:")
                hdparm = subprocess.run(["sudo", "hdparm", "-I", f"{self.partition}"], capture_output=True)
                subprocess.check_output(["grep", "-i", "erase unit"], input=hdparm.stdout)
                # subprocess.run(["sudo", "hdparm", "--user-master", "u", "--security-erase", f"{self._pass_hdparm}", f"{self.partition}"])
                click.echo("Successfully finished Security Erase!")
            case 3:
                click.secho("You selected Block Erase", fg="magenta")
                # Code for option 3
                click.echo("This mode raises each block to a voltage higher than the standard program voltage (erase voltage), and drops it to ground, leaving no trace of previous signal\n")
                click.echo("Checking compatibility...\n")
                self._chk_sanitize_status()
                click.echo("Please wait... this may take a long time.")
                # subprocess.run(["sudo", "hdparm", "--sanitize-block-erase", f"{self.partition}"])
                click.echo("Successfully finished Block Erase!")
            case 4:
                click.secho("You selected Crypto Scramble Erase", fg="magenta")
                click.echo("This mode rotates the internal cryptographic key used in self-encrypting drives, potentially rendering data unreadable if the encryption algorithm is strong\n")
                click.echo("Checking compatibility...")
                self._chk_sanitize_status()
                click.echo("Please wait... this may take a long time.")
                # subprocess.run(["sudo", "hdparm", "--sanitize-crypto-scramble", f"{self.partition}"])
                click.echo("Successfully finished Security Erase!")
    
    
    def auto_wipe(self):
        click.secho("You selected Automatic Wipe...", fg="magenta")
        click.echo("This method checks each method for its compatibility and executes the best method")
        list_partitions()
        click.echo("\nIf you want to wipe the whole drive, partitioned as sda1, sda2, ..., sdaN; select /dev/sda")
        self.partition = click.prompt("Enter your device's partition", default="/dev/sda")
        if not validate_partition(self.partition):
            raise click.Abort

        click.echo("Trying ATA Secure Erase...")
        self._install_tool("hdparm")
        hdparm_output= subprocess.check_output(["sudo", "hdparm", "--sanitize-status", f"{self.partition}"], text=True)
        if "sanitize feature" in hdparm_output:
            click.echo(f"ATA Secure Erase is compatible for {self.partition}!\n")
            self.ata_hdparm()
            return
        click.secho(f"ATA Secure Erase is not compatible for {self.partition}. Trying SATA Secure Erase...", fg="yellow")
 
        self._install_tool("sg3-utils")
        sg_output = subprocess.check_output(["sudo", "sg_sanitize", "-C", "-z", "-Q", f"{self.partition}"], text=True)
        if "fail" in sg_output:
            click.echo(f"SATA Secure Erase is compatible for {self.partition}!")
            return
        click.echo(f"SATA Secure Erase is not compatible for {self.partition}. Trying NVMe Secure Erase...\n")
   
        self._install_tool("nvme-cli")
        nvme_output= subprocess.check_output(["sudo", "nvme", "id-ctrl", f"{self.partition}", "-H"], text=True)
        if "invalid" in nvme_output:
            click.echo(f"NVMe Secure Erase is compatible for {self.partition}!\n")
            return
        click.echo(f"NVMe Secure Erase is not compatible for {self.partition}. Falling back to cryptographic wipe method...\n")
        self.crypt_wipe()

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
@click.option("--method", "-m", type=click.IntRange(1, 6), callback=validate_sanitize, is_eager=False)
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
        value = click.prompt("Enter your device's partition", default="/dev/sda")
        valid_partition = validate_partition(value)
        if valid_partition:
            return valid_partition
        ctx.abort()
    return value
        
        
@click.command()
@click.option("--partition", "-p", type=click.Path(exists=True, readable=False, resolve_path=True), callback=validate_extract, is_eager=False)
@click.option("--bytesize", "-b", default="1M", help="""
                N and BYTES may be followed by the following multiplicative suffixes:
                c =1, w =2, b =512, kB =1000, K =1024, MB =1000*1000, M =1024*1024, xM =M,
                GB =1000*1000*1000, G =1024*1024*1024, and so on for T, P, E, Z, Y.
                """)
def extract(partition, bytesize):
    """Extraction command"""
    loc = click.prompt("Enter ouput location for the bin file (/path/to/your/image.bin)")
    loc = os.path.expandvars(loc) # To handle input with $ symbols like $HOME, $PATH, etc.
    loc = os.path.expanduser(loc) # To handle input with "~" or "~user" in input prompt
    subprocess.run(["sudo", "dd", f"if={partition}", f"of={loc}", f"bs={bytesize}", "status=progress"])
    

@click.command()
def verify():
    """Verification command"""
    click.secho("You selected verify...", fg="magenta")
    click.echo("Command line forensic verification tool is yet to be added...\n")
    click.echo("Verification is done by checking for recoverable files. This can be done in many ways.")
    click.echo("The one I know and use is Autopsy, an open source application used for Forensics by Investigators and Law Enforcement officials or curious minds.")
    click.echo("It can recover files from disk images. Bin dumps are disk images which can be extracted using the available Imaging process.")
    click.echo("The detailed process for verification is as follows:\n")
    click.echo("Work in Progress...")

@click.group()
def main():
    """A linux command line utility for storage sanitization. 
    Developed for IoT devices with shell access, keeping modern flash storages like SSDs in mind.
    
    Main commands:\n
    1) sanitize: Sanitization (Wiping)\n
    2) extract: Extraction (Imaging)\n
    3) verify: Verification (External process)
    """
    pass

if __name__ == '__main__':
    main.add_command(sanitize)
    main.add_command(extract)
    main.add_command(verify)
    main()
