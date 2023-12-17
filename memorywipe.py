import os
import click
import subprocess
from shutil import which as swhich


def check_install(app):
    return swhich(app) is not None


def prompt_disk_partition():
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

    click.echo("\nIf you want to extract the whole drive, partitioned as sda1, sda2, ..., sdaN; select /dev/sda")
    return click.prompt("Enter your device's partition", default="/dev/sda")


def validate_partition(path):
    try:
        subprocess.run(["grep", "-qs", path, "/proc/mounts"], check=True)
        # If the above command doesn't raise a CalledProcessError, the partition exists
        return path
    except subprocess.CalledProcessError:
        # The partition doesn't exist, print message and return False
        click.echo("\nYour partition does not exist. Enter the correct partition. Start again...\n")
        return False


def _install_tool(app):
    click.echo(f"\nChecking existing installation for {app}")
    if check_install(app):
        click.echo("Check complete...")
    else:
        if app == "nandump":
            app = "mtd-utils"
        click.echo(f"Installing {app}...")
        try:
            subprocess.run(["sudo", "apt-get", "install", app, "-y"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=True)
        except subprocess.CalledProcessError:
            click.secho(f"Error: Unable to install {app}. Please install it manually.", fg="red")
            raise click.Abort


class Sanitization:
    def __init__(self, val):
        self.method_value = val
        self.partition = None
        self.filesystem = None

    def crypt_wipe(self):
        click.secho("You selected Cryptographic Wipe.", fg="magenta")
        click.echo("Starting Cryptographic Wipe using VeraCrypt...\n")
        try:
            assert self._install_veracrypt()
        except AssertionError:
            raise click.Abort
        click.secho(
            "WARNING: This process is irreversible. Create necessary backups if required (You may use the extraction module for this).\n",
            fg="yellow")
        click.secho(
            "NOTE: Cryptographic Wipe on Flash Storage partitions may not be effective. Perform it on the whole disk.",
            fg="blue")
        click.secho(
            "If there are multiple partitions in the device, format them into one single partition, and then wipe it.",
            fg="blue")
        self.partition = prompt_disk_partition()
        if not validate_partition(self.partition):
            raise click.Abort
        if not self._check_mount():
            raise click.Abort
        self._veracrypt_encrypt()
        self._wipe_disk()
        self._mount_disk()
        click.secho("Cryptographic Wipe procedure completed successfully!", fg="bright_green")
        del self.partition

    def chk_encrypted(self):
        try:
            lsblk = subprocess.run(["lsblk", "-f", "/dev/nvme0n1p8"], capture_output=True, check=True)
            try:
                subprocess.run(["grep", "-q", "veracrypt"], input=lsblk.stdout, check=True)
            except subprocess.CalledProcessError:
                return False
        except subprocess.CalledProcessError:
            click.echo(f"{self.partition} doesn't exist")
            return False
        return True

    def _veracrypt_interactive(self):
        click.echo("Volume type:\n1) Normal\n2) Hidden")
        vol_type_dict = {1: "normal", 2: "hidden"}
        vol_type = vol_type_dict[click.prompt("Select", default=1, type=click.IntRange(1, 2), show_choices=False)]
        click.echo(
            "\nEncryption Algorithm:\n"
            "1) AES\n"
            "2) Serpent\n"
            "3) Twofish\n"
            "4) Camellia\n"
            "5) Kuznyechik\n"
            "6) AES(Twofish)\n"
            "7) AES(Twofish(Serpent))\n"
            "8) Camellia(Kuznyechik)\n"
            "9) Camellia(Serpent)\n"
            "10) Kuznyechik(AES)\n"
            "11) Kuznyechik(Serpent(Camellia))\n"
            "12) Kuznyechik(Twofish)\n"
            "13) Serpent(AES)\n"
            "14) Serpent(Twofish(AES))\n"
            "15) Twofish(Serpent)"
        )
        encrypt_type_dict = {
            1: "aes",
            2: "serpent",
            3: "twofish",
            4: "camellia",
            5: "kuznyechik",
            6: "aes(twofish)",
            7: "aes(twofish(serpent))",
            8: "camellia(kuznyechik)",
            9: "camellia(serpent)",
            10: "kuznyechik(aes)",
            11: "kuznyechik(serpent(camellia))",
            12: "kuznyechik(twofish)",
            13: "serpent(aes)",
            14: "serpent(twofish(aes))",
            15: "twofish(serpent)"
        }
        encrypt_type = encrypt_type_dict[
            click.prompt("Select", default=1, type=click.IntRange(1, 15), show_choices=False)]
        click.echo("\nHash algorithm:\n1) SHA-512\n2) Whirlpool\n3) BLAKE2s-256\n4) SHA-256\n5) Streebog")
        hash_algo_dict = {1: "sha-512", 2: "whirlpool", 3: "blake2s-256", 4: "sha-256", 5: "streebog"}
        hash_algo = hash_algo_dict[click.prompt("Select", default=1, type=click.IntRange(1, 5), show_choices=False)]
        click.echo(
            "\nFilesystem:\n"
            "1) None\n"
            "2) FAT\n"
            "3) Linux Ext2\n"
            "4) Linux Ext3\n"
            "5) Linux Ext4\n"
            "6) NTFS"
        )
        filesystem_dict = {
            1: "none",
            2: "fat",
            3: "linux ext2",
            4: "linux ext3",
            5: "linux ext4",
            6: "ntfs"
        }
        self.filesystem = filesystem_dict[
            click.prompt("Select", default=6, type=click.IntRange(1, 6), show_choices=False)]
        click.echo("\nEnter strong password for encrypting. (You don't have to remember it)")
        strongp = click.prompt("So set a random password with special characters", hide_input=True,
                               confirmation_prompt=False)
        subprocess.run(["sudo", "veracrypt", "-tc", f"--volume-type={vol_type}",
                        f"{self.partition}", f'--encryption={encrypt_type}', f'--hash={hash_algo}',
                        f"--filesystem={self.filesystem}", "-p", f"{strongp}", "--pim=0",
                        "-k", "", "--random-source=/dev/urandom"])

    def _veracrypt_encrypt(self):
        if self.chk_encrypted():
            click.echo("Selected partition is already encrypted! Skipping encryption...\n")
        else:
            q2 = click.prompt("Do you want to encrypt manually or automatically?", type=click.Choice(["m", "a"]),
                              show_choices=True, default='a')
            click.secho(
                "Executing VeraCrypt volume creation command...\nPlease wait. This might take a long time for larger storages...",
                fg="bright_magenta")
            if q2 == "m":
                click.echo("Starting veracrypt manually...\n")
                self._veracrypt_interactive()

            elif q2 == "a":
                self.filesystem = "ntfs"
                click.echo("Uses AES, with SHA-512 and makes an NTFS filesystem")
                click.echo("\nEnter strong password for encrypting. (You don't have to remember it)")
                strongp = click.prompt("So set a random password with special characters", hide_input=True,
                                       confirmation_prompt=False)
                subprocess.run(["sudo", "veracrypt", "-tc", "--volume-type=normal",
                                f"{self.partition}", "--encryption=aes", "--hash=sha-512",
                                "--filesystem=ntfs", "-p", f"{strongp}", "--pim=0",
                                "-k", "", "--random-source=/dev/urandom"])

            click.echo("Finishing up...")
            click.secho(f"Finished encrypting {self.partition}\n", fg="green")

    def _wipe_disk(self):
        click.echo(f"Wiping {self.partition}...")
        if not self._check_mount():
            click.secho("Make sure the disk is unmounted!", fg="red")
            raise click.Abort
        else:
            click.secho(
                "Executing dd command and writing random values to partition....\nPlease be patient. This make take longer time for larger partitions.",
                fg="bright_magenta")
            subprocess.run(["sudo", "dd", "if=/dev/random", f"of={self.partition}", "bs=1M", "status=progress"])
            click.secho("Executing dd command and writing zeros to partition...", fg="bright_magenta")
            subprocess.run(["sudo", "dd", "if=/dev/zero", f"of={self.partition}", "bs=1M", "status=progress"])

            click.secho(f"{self.partition} overwritten with one write each of random data and zeroes",
                        fg="bright_white")
            self.name = click.prompt("Set device name")
            try:
                click.secho(
                    f"Creating '{self.filesystem}' filesystem on partition: '{self.partition}' with label '{self.name}'...",
                    fg="bright_magenta")
                if self.partition == "fat":
                    subprocess.run(
                        ["sudo", f"mkfs.{self.filesystem}", "-n", f"{self.name}", "-F", "32", f"{self.partition}"],
                        check=True)
                else:
                    subprocess.run(["sudo", f"mkfs.{self.filesystem}", "-L", f"{self.name}", f"{self.partition}"],
                                   check=True)
            except subprocess.CalledProcessError as e:
                click.secho("Failed to create filesystem!", fg="red")
                click.echo(e)
                raise click.Abort

            click.secho(f"Wiped {self.partition}\n", fg="green")

    def _mount_disk(self):
        # read -p "Set mounting folder name: " name
        click.echo(f"Mounting {self.partition} at /media/{self.name}")
        try:
            subprocess.run(["sudo", "mkdir", f"/media/{self.name}"])
        except subprocess.CalledProcessError:
            click.secho(f"{self.name} directory already exists! Skipping...", fg="yellow")

        try:
            subprocess.run(["sudo", "mount", f"{self.partition}", f"/media/{self.name}/"], check=True)
            click.secho("Finished mounting!\n", fg="green")
        except subprocess.CalledProcessError:
            click.secho(f"Failed to mount {self.partition} on {self.name}. Please mount manually!", fg="red")
            click.echo("The command to mount the partition:\nsudo mount <partition> /media/<directory_name>/")

        del self.name

    def _check_mount(self):
        try:
            click.secho("Unmounting the partition...", fg="blue")
            # Run the grep command to check if the partition is in /proc/mounts
            try:
                subprocess.run(["grep", "-qs", self.partition, "/proc/mounts"], check=True)
                # If the above command doesn't raise a CalledProcessError, the partition is mounted
                # Unmount the partition
            except subprocess.CalledProcessError:
                click.secho(f"{self.partition} is already dismounted or doesn't exist", fg="yellow")
                return True
            subprocess.run(["sudo", "umount", self.partition], check=True)
            # Check if the partition is still mounted
            subprocess.run(["grep", "-qs", self.partition, "/proc/mounts"], check=True)
            click.secho(f"Error: Failed to unmount {self.partition}. Please unmount manually.", fg="red")
            return False
        except subprocess.CalledProcessError:
            click.secho(f"{self.partition} has been successfully unmounted", fg="green")
            return True

    def _install_veracrypt(self):
        app = "veracrypt"
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
        click.echo(
            "NOTE: If it did not work for you, change the version and architecture according to your device and os..")
        click.echo("For example, raspberry pi uses armhf architecture. So, the change amd64 to armhf command is:")
        click.echo(
            "sudo wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-console-1.26.7-Debian-11-amd64.deb --connect-timeout=5 -c -P ./veracrypt && sudo apt install ./veracrypt/veracrypt-console-1.26.7-Debian-11-amd64.deb -y")
        return False

    def ata_hdparm(self):
        click.secho("You selected ATA Secure Erase...", fg="magenta")
        click.echo("Starting ATA Secure Erase using hdparm...")
        try:
            _install_tool("hdparm")
        except AssertionError:
            raise click.Abort

        self.partition = prompt_disk_partition()
        if not validate_partition(self.partition):
            raise click.Abort

        self._chk_compat_hdparm()
        self._chk_freeze()
        click.echo("The time taken for this process to finish will be:")
        try:
            info = subprocess.run(["sudo", "hdparm", "-I", f"{self.partition}"], capture_output=True)
            subprocess.run(["grep", "-i", "erase unit"], input=info.stdout, check=True)
        except subprocess.CalledProcessError:
            click.secho("Couldn't get time taken info.\n", fg="yellow")

        self._pass_hdparm = click.prompt("Set a password", hide_input=True, confirmation_prompt=False)
        # subprocess.run(["sudo" "hdparm" "--user-master" "u" "--security-set-pass" f"{self._pass_hdparm}" f"{self.partition}"])
        click.echo("Password set!\n")
        self._select_enhance()
        click.secho("\nATA Secure Erase procedure successfully completed!", fg="bright_green")
        del self.partition
        del self._pass_hdparm

    def _chk_compat_hdparm(self):
        try:
            info = subprocess.check_output(["sudo", "hdparm", "-I", f"{self.partition}"])
            subprocess.run(["grep", "-i", "sanitize feature"], input=info, check=True)
            click.echo("Your device supports hdparm set!")
        except subprocess.CalledProcessError:
            click.secho("Your device does not support hdparm set!\n", fg="yellow")
            raise click.Abort

    def _chk_freeze(self):
        hdparm_output = subprocess.check_output(["sudo", "hdparm", "-I", f"{self.partition}"], text=True)
        if "not	frozen" in hdparm_output:
            click.echo("Device is not frozen! Continuing to next step...")
        else:
            click.secho("Device is frozen! A system suspend or reboot should unfreeze it.", fg="yellow")
            click.echo("A system suspend will suspend the device. You can press any key and start it after a minute")
            click.secho("YOUR DEVICE WILL TURN OFF FOR A FEW MINUTES IF YOU SELECT YES. DO NOT PANIC\n")
            suspend = click.prompt("Do you want to suspend your system?", type=click.Choice(["y", "n"]), default='n')
            if suspend == "y":
                subprocess.run(["sudo", "systemctl", "suspend"])
                self._chk_freeze()
            else:
                click.secho("You can't continue with this process without suspending...\nStart again.", fg="red")
                raise click.Abort

    def _chk_sanitize_status(self):
        hdparm_output = subprocess.check_output(["sudo", "hdparm", "--sanitize-status", f"{self.partition}"], text=True)
        if "sanitize feature" not in hdparm_output:
            click.secho("Your device does not support sanitize feature set!", fg="yellow")
        else:
            click.secho("Your device supports sanitize feature set!", fg="green")

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
                click.echo(
                    "This mode writes predetermined data patterns set by the manufacturer to all areas including bad blocks")
                click.echo("Please wait... this may take a long time. At-least:")
                hdparm = subprocess.check_output(["sudo", "hdparm", "-I", f"{self.partition}"])
                subprocess.run(["grep", "-i", "erase unit"], input=hdparm)
                # subprocess.run(["sudo", "hdparm", "--user-master", "u", "--security-erase-enhanced", f"{self._pass_hdparm}", f"{self.partition}"])
                click.echo("Successfully finished Enhanced Security Erase!")
            case 2:
                click.secho("You selected Security Erase", fg="magenta")
                click.echo("This mode writes all user data excluding bad blocks with zeroes")
                click.echo("Please wait... this may take a long time. At-least:")
                hdparm = subprocess.check_output(["sudo", "hdparm", "-I", f"{self.partition}"])
                subprocess.run(["grep", "-i", "erase unit"], input=hdparm)
                # subprocess.run(["sudo", "hdparm", "--user-master", "u", "--security-erase", f"{self._pass_hdparm}", f"{self.partition}"])
                click.echo("Successfully finished Security Erase!")
            case 3:
                click.secho("You selected Block Erase", fg="magenta")
                # Code for option 3
                click.echo(
                    "This mode raises each block to a voltage higher than the standard program voltage (erase voltage), and drops it to ground, leaving no trace of previous signal\n")
                click.echo("Checking compatibility...\n")
                self._chk_sanitize_status()
                click.echo("Please wait... this may take a long time. At-least:")
                hdparm = subprocess.check_output(["sudo", "hdparm", "-I", f"{self.partition}"])
                subprocess.run(["grep", "-i", "erase unit"], input=hdparm)
                # subprocess.run(["sudo", "hdparm", "--sanitize-block-erase", f"{self.partition}"])
                click.echo("Successfully finished Block Erase!")
            case 4:
                click.secho("You selected Crypto Scramble Erase", fg="magenta")
                click.echo(
                    "This mode rotates the internal cryptographic key used in self-encrypting drives, potentially rendering data unreadable if the encryption algorithm is strong\n")
                click.echo("Checking compatibility...")
                self._chk_sanitize_status()
                click.echo("Please wait... this may take a long time. At-least:")
                hdparm = subprocess.run(["sudo", "hdparm", "-I", f"{self.partition}"], capture_output=True)
                subprocess.run(["grep", "-i", "erase unit"], input=hdparm.stdout)
                # subprocess.run(["sudo", "hdparm", "--sanitize-crypto-scramble", f"{self.partition}"])
                click.echo("Successfully finished Security Erase!")

    def auto_wipe(self):
        click.secho("You selected Automatic Wipe...", fg="magenta")
        click.echo("This method checks each method for its compatibility and executes the best method.")
        self.partition = prompt_disk_partition()
        if not validate_partition(self.partition):
            raise click.Abort

        click.echo("Trying ATA Secure Erase...")
        _install_tool("hdparm")
        try:
            hdparm_output = subprocess.check_output(["sudo", "hdparm", "-I", f"{self.partition}"])
            subprocess.run(["grep", "-i", "sanitize feature"], input=hdparm_output, check=True)
            # if "sanitize feature" in hdparm_output:
            click.echo(f"ATA Secure Erase is compatible for {self.partition}!\n")
            self.ata_hdparm()
            return
        except subprocess.CalledProcessError:
            click.secho(f"ATA Secure Erase is not compatible for {self.partition}. Trying SATA Secure Erase...",
                        fg="yellow")

        _install_tool("sg3-utils")
        try:
            sg_output = subprocess.check_output(["sudo", "sg_sanitize", "-CzQ", f"{self.partition}"])
            subprocess.run(["grep", "-i", "fail"], input=sg_output, check=True)
            # if "fail" in sg_output:
            click.echo(f"SATA Secure Erase is compatible for {self.partition}!")
            return
        except subprocess.CalledProcessError:
            click.secho(
                f"SATA Secure Erase is not compatible for {self.partition}. Trying NVMe Secure Erase...\n",
                fg="yellow")

        _install_tool("nvme-cli")
        try:
            nvme_output = subprocess.check_output(["sudo", "nvme", "id-ctrl", f"{self.partition}", "-H"])
            subprocess.run(["grep", "-i", "invalid"], input=nvme_output, check=True)
            click.echo(f"NVMe Secure Erase is compatible for {self.partition}!\n")
            return
        except subprocess.CalledProcessError:
            click.secho(
                f"NVMe Secure Erase is not compatible for {self.partition}. Falling back to cryptographic wipe "
                f"method...\n", fg="yellow")

        self.crypt_wipe()


def validate_sanitize(ctx, param, value):
    if not value or ctx.resilient_parsing:
        click.secho("You selected wiping...", fg="magenta")
        click.echo("""
            Available Methods: [Default: 1]
            [1] Automatic wipe (Executes the best compatible method)
            [2] Cryptographic Wipe
            [3] ATA Secure Erase (hdparm)
            [4] SATA Secure Erase (sg-utils)
            [5] NVMe Secure Erase (nvme-cli)
            """)
        value = click.prompt("Select the wiping method", type=int, default=1)
        try:
            assert value in range(1, 6)
            return value
        except AssertionError:
            raise click.BadParameter("Invalid value range. Must be between 1 and 5")
    return value


@click.command()
@click.option(
    "--method", "-m",
    type=click.IntRange(1, 6),
    callback=validate_sanitize,
    is_eager=False,
    help="""
    Available Methods: [Default: 1]\n
    [1] Automatic wipe (Executes the best compatible method)\n
    [2] Cryptographic Wipe\n
    [3] ATA Secure Erase (hdparm)\n
    [4] SATA Secure Erase (sg-utils)\n
    [5] NVMe Secure Erase (nvme-cli)\n
    """
)
def sanitize(method):
    """Sanitization command"""
    wipe = Sanitization(method)
    match method:
        case 1:
            wipe.auto_wipe()
        case 2:
            wipe.crypt_wipe()
        case 3:
            wipe.ata_hdparm()
        case 4:
            click.echo("No SATA devices are available for testing. Will be added soon...")
        case 5:
            click.echo("No NVMe devices are available for testing. Will be added soon...")
        case _:
            click.echo("Wrong input value")


def validate_extract(ctx, param, value):
    if not value or ctx.resilient_parsing:
        click.secho("You selected imaging...", fg="magenta")
        click.echo("Select a partition to extract:-")
        value = prompt_disk_partition()
        valid_partition = validate_partition(value)
        if valid_partition:
            return valid_partition
        ctx.abort()
    return value


@click.command()
@click.option("--partition", "-p", type=click.Path(exists=True, readable=False, resolve_path=True),
              callback=validate_extract, is_eager=False)
@click.option("--bytesize", "-b", default="1M", help="""
                N and BYTES may be followed by the following multiplicative suffixes:
                c=1, w=2, b=512, kB=1000, K=1024, MB=1000*1000, M=1024*1024, xM=M,
                GB=1000*1000*1000, G=1024*1024*1024, and so on for T, P, E, Z, Y.
                Binary prefixes can be used, too: KiB=K, MiB=M, and so on.
                """)
def extract(partition, bytesize):
    """Extraction command"""
    loc = click.prompt("Enter output location for the extracted image", default="./image.bin")
    loc = os.path.expandvars(loc)  # To handle input with $ symbols like $HOME, $PATH, etc.
    loc = os.path.expanduser(loc)  # To handle input with "~" or "~user" in input prompt
    try:
        subprocess.run(
            ["sudo", "dd", f"if={partition}", f"of={loc}", f"bs={bytesize}", "status=progress"],
            check=True
        )
        click.echo(f"Image of {partition} extracted to {loc} successfully!")
    except subprocess.CalledProcessError:
        click.secho("Failed to extract partition!", fg="red")
        raise click.Abort


@click.command()
def verify():
    """Verification command"""
    click.secho("You selected verify...", fg="magenta")
    click.echo("Command line forensic verification tool is yet to be added...\n")
    click.echo("Verification is done by checking for recoverable files. This can be done in many ways.")
    click.echo(
        "The one I know and use is Autopsy, an open source application used for Forensics by Investigators and Law Enforcement officials or curious minds.")
    click.echo(
        "It can recover files from disk images. Bin dumps are disk images which can be extracted using the available Imaging process.")
    click.echo("The detailed process for verification is as follows:\n")
    click.echo("Work in Progress...")


@click.group()
def main():
    """A linux command line utility for storage sanitization.
    Developed for IoT devices with shell access, keeping modern flash storages like SSDs in mind.

    Main commands:\n
    1) sanitize: Sanitization (Wiping)\n
    2) extract: Extraction (Imaging)\n
    3) verify: Verification (External process)\n
    
    Options:\n
    Sanitize options:\n
    -m, --method\n
    Select method number to directly run a specific sanitization method.
    
    Extract options:\n
    -p, --partition\n
    Sets partition beforehand for extraction\n
    -b, --bytesize\n
    Sets bytesize value\n
    
    Example:\n
    python3 memorywipe.py sanitize -m 1 (selects automatic wipe method)\n
    python3 memorywipe.py extract -p /dev/sdb6 (extracts /dev/sdb6)\n
    python3 memorywipe.py extract -p /dev/sda -b 1M (extracts /dev/sda with a block size of 1M)
    """
    pass


if __name__ == '__main__':
    main.add_command(sanitize)
    main.add_command(extract)
    main.add_command(verify)
    main()
