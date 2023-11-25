#!/bin/bash

#Only the functions defined before the case statement can be called inside it.

# Checks if a certain program is installed or not
#read -p "Enter the application name: " app #If you want to take the user input
chk_install() {
  local command_name="$1"
  if command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is installed."
    return 0
  else
    echo "$command_name is not installed"
    return 1
  fi

  #Usage in other functions:
  #Define required variables first. Then run chk_install. Finally check the result.
  # app="tool name"
  # chk_install "$app"
  # install_result=$?
  # if [ $install_result -eq 0 ]; then
  # 	echo "Tool...Check!"
  # else
  # 	echo "Tool is not installed"
  #	#Installation code here
}

# Check partitions
list_partitions() {
  valid_input=false
  while true; do
    read -p "Do you want to see all the partitions?(y/n)[n]: " q1
    if [ "$q1" = "y" ]; then
      valid_input=true
      break
    else
      if [ "$q1" = "n" ] || [ -z "$q1" ]; then #adding -z part made null input default to "n".
        break
      else
        echo "Invalid input. Please give either 'y' or 'n'" 
	echo
      fi
    fi
  done
  if [ "$valid_input" = true ]; then
    app="lsblk"
    chk_install "$app" >/dev/null 2>&1
    install_result=$?
    if [ $install_result -eq 0 ]; then
      lsblk -f
    else
      df -hT
    fi
  fi
  #df -hT | grep '^/dev/' | awk 'BEGIN {printf "%-20s %-10s %-30s\n", "Filesystem", "Type", "Mounted on"} {printf "%-20s %-10s %-30s\n", $1, $2, $7}'
  #`^` is for select entries starting, similar to how `*` is for select everything.
  #%-20s will make left aligning column of minimum 20 character length, useful to make columns evenly spaced.
  #This method can be used to print particular columns and devices instead of everything.
}

### --- Cryptographic wipe starts here ---
# Installing veracrypt
ins_veracrypt() {
  app="veracrypt"
  echo "Checking for existing $app installation..."
  #echo "Install result is: $install_result"
  #chk_install "$app" > /dev/null 2>&1  # If you want to suppress the output
  chk_install "$app"
  install_result=$?

  if [ $install_result -eq 0 ]; then
    echo "Check complete..."
  else
    echo "Installing VeraCrypt..."
    sudo wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-console-1.26.7-Debian-11-armhf.deb --connect-timeout=5 -c -P ./veracrypt >/dev/null 2>&1 && sudo apt install ./veracrypt/veracrypt-console-1.26.7-Debian-11-armhf.deb -y >/dev/null 2>&1

    echo "Checking for successful installation"
    app="veracrypt"
    chk_install "$app"
    install_result=$?
    if [ $install_result -eq 0 ]; then
      echo "Check complete..."
    else
      echo "VeraCrypt installation failed!! Install manually."
      echo
      echo "NOTE: If it did not work for you, change the version and architecture according to your device and os..."
      echo "For example, raspberry pi uses armhf architecture. So, the change amd64 to armhf command is:"
      echo "sudo wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-console-1.26.7-Debian-11-amd64.deb --connect-timeout=5 -c -P ./veracrypt && sudo apt install ./veracrypt/veracrypt-console-1.26.7-Debian-11-amd64.deb -y"
      exit
    fi
  fi
  #sudo -S <<(echo "pass")>> wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-1.26.7-setup.tar.bz2 --connect-timeout=5 -c -P ./veracrypt/ && sudo -S <<(echo "pass")>> tar xjf ./veracrypt/veracrypt* -C ./veracrypt
}

# Checks if the partition is unmounted
chk_unmount() {
  #ISSUE: If the target partition /dev/sda1 is already unmounted, and the user gives sda1 as input, it does not work as intended.
  #sda1 will not be found in the /proc/mounts, so it says successfully unmounted, but sda1 is not even a block device.
  #read -p "Enter your device's partition (/dev/sdb1): " partition
  echo "Unmounting the partition..."

  if grep -qs "$partition" /proc/mounts; then
    sudo umount $partition
    if grep -qs "$partition" /proc/mounts; then
      echo "Error: Failed to unmount $partition. Unmount manually."
      return 1
    else
      echo "$partition has been successfully unmounted."
      return 0
    fi
  else
    echo "$partition already unmounted"
    return 0
  fi
}

# Check if partition is already encrypted by veracrypt (to prevent wasting time unless needed)
chk_encrypted() {
  command=$(lsblk -f $partition)
  # Check if there is a partition with the name "veracrypt"
  if echo "$command" | grep -q "veracrypt"; then
    return 0
  else
    return 1
  fi
}

# Actual encryption process using veracrypt
veracrypt_encrypt() {
  if chk_encrypted; then
    echo "Selected partition is already encrypted! Skipping encryption..."
  else
  #https://kifarunix.com/how-to-use-veracrypt-on-command-line-to-encrypt-drives-on-ubuntu/
    read -p "Do you want to encrypt manually or automatically? (m/a)[a]: " q2
    if [ "$q2" = "m" ]; then
      echo "Starting veracrypt manually..."
      sudo veracrypt -t -c
    else
      if [ "$q2" = "a" ] || [ -z "$q2" ]; then #adding -z part made null input default to "n".
          echo "Uses AES, with SHA-512 and makes an NTFS filesystem"
	  echo
	  echo "Enter strong password for encrypting. (You don't have to remember it)"
	  read -p "So set a random password with special characters: " strongp
	  sudo veracrypt -t -c --volume-type=normal $partition --encryption=aes --hash=sha-512 --filesystem=ntfs -p $strongp --pim=0 -k "" --random-source=/dev/urandom
    echo "Finished encrypting $partition"
	  #sudo veracrypt -t $partition /media/ -p $strongp --pim=0 -k "" --protect-hidden=no #To mount the veracrypt volume
	  #sudo veracrypt -d $partition #Unmount the veracrypt volume
      else
	echo "Invalid input. Please give either 'm' or 'a'" 
      fi
    fi
  fi
}

# Wipes the disk
wipe_disk() {
  echo "Wiping $partition..."
  if chk_unmount; then
    sudo dd if=/dev/random of=$partition bs=1M status=progress
    #sudo dd if=/dev/random of=$partition bs=1M status=progress > /dev/null 2>&1
    sudo dd if=/dev/zero of=$partition bs=1M status=progress
    echo "$partition overwritten with one write each of random data and zeroes"
    read -p "Set device name: " name
    sudo mkfs.ntfs -L $name $partition #Should automate to allow partitioning into different filesystems
    echo "Wiped $partition"
    return 0
  else
    echo
    echo "Wipe failed! Make sure the disk is unmounted!"
    return 1
  fi
}

# Mounts disk at /media/$name
mount_disk() {
  #read -p "Set mounting folder name: " name
  echo "Mounting $partition at /media/$name"
  sudo mkdir /media/$name > /dev/null 2>&1
  sudo mount $partition /media/$name/
  echo "Finished mounting!"
}

# Sanitization - Cryptographic wipe, works on any device that supports encryption tools (VeraCrypt - most compatible)
crypt_wipe() {
  echo "Starting Cryptographic Wipe using VeraCrypt..."
  echo
  ins_veracrypt #Script should not proceed if this step fails.
  echo

  echo "WARNING: This process is irreversible. Create necessary backups if required (You may use the extraction module for this)."
  echo
  echo "NOTE: Cryptographic Wipe on Flash Storage partitions may not be effective. Perform it on the whole disk."
  echo "If there are multiple partitions in the device, format them into one single partition, and then wipe it."
  echo
  list_partitions

  # Setting a value for partition (/dev/sdb1) to wipe
  echo
  echo "Select /dev/sda, if you want to wipe the whole drive, partitioned as sda1, sda2, ..., sdaN"
  read -p "Enter your device's partition (/dev/sda1): " partition
  echo
  
  # Making sure disk is unmounted
  if chk_unmount; then
    echo
  else
    echo "Unmounting failed!! Please unmount manually before proceeding"
    echo
    return 1
  fi
  
  # Start the process
  veracrypt_encrypt
  echo
  wipe_disk
  echo
  mount_disk 
  echo
  echo "Cryptographic Wipe procedure completed successfully!"
}
### --- Cryptographic Wipe ends here ---

### ---ATA Secure Erase starts here ---
# Installing hdparm
ins_hdparm() {
  app="hdparm"
  echo
  echo "Checking existing installation for $app" 
  chk_install "$app"
  install_result=$?
  
  if [ $install_result -eq 0 ]; then
    echo "$app...Check!"
  else
    echo "Installing $app..."
    sudo apt-get install $app -y >/dev/null 2>&1 || {
      echo "Error: Unable to install $app. Please install it manually."
      exit 1
    }
  fi
}

# Sanitization - devices with ATA SECURE ERASE enabled using hdparm
ata_hdparm() {
  ins_hdparm
  #Check sudo hdparm -I $partition | grep SANITIZE to find if it is supported
}
### --- ATA Secure Erase ends here ---

# Extraction - mtd devices using nanddump
ins_nanddump() {
  app="nanddump" 
  echo
  echo "Checking existing installation for $app..."
  chk_install "$app"
  install_result=$?
  #echo "Install result is: $install_result"

  if [ $install_result -eq 0 ]; then
    echo "$app...Check!"
  else
    echo "Installing mtd-utils..."
    sudo apt-get install mtd-utils -y >/dev/null 2>&1 || {
      echo "Error: Unable to install mtd-utils. Please install it manually."
      exit 1
    }
  fi
  #sudo -S <<(echo "$pass") apt install mtd-utils -y #If there ever comes a need to input sudo password automatically.
  #nanddump -s /dev/sda7 --bb='dumpbad' -p -n -c
  #echo
}

main() {

  echo "Available actions: "
  echo "[1] Sanitization (Wiping)"
  echo "[2] Extraction (Imaging)"
  echo "[3] Verification (External process)"

  read -p "Select your purpose: " purpose
  echo
  case $purpose in
  1)
    echo "You selected Wiping"
    # Code for option 1
    echo "Available Methods: "
    echo "[1] Cryptographic Wipe"
    echo "[2] ATA Secure Erase (hdparm)"
    echo "[3] Diskpart"

    read -p "Select your wiping method: " wipe
    echo
    case $wipe in
    1)
      echo "You selected Cryptographic Wipe"
      # Code for option 1
      crypt_wipe
      ;;
    2)
      echo "You selected ATA Secure Erase using hdparm"
      # Code for option 2
      ;;
    3)
      echo "You selected diskpart"
      # Code for option 3
      ;;

    esac
    ;;
  2)
    echo "You selected Extraction"
    # Code for option 2
    ins_nanddump
    ;;
  3)
    echo "You selected Verification"
    # Code for option 3
    echo "Verification is done by checking for recoverable files. This can be done in many ways."
    echo "The one I know and use is Autopsy, an open source application used for Forensics by Investigators and Law Enforcement officials or curious minds."
    echo "It can recover files from disk images. Bin dumps are disk images which can be extracted using the available Imaging process."
    echo "The detailed process for verification is as follows:"
    ;;
  *)
    echo "Invalid option! Select from 1, 2, 3."
    main
    ;;
  esac
}

#Without this below part from bard, the above input_validation() function is not running. Have to understand this better.
input_valid=false

while [ "$input_valid" = false ]; do
  if main; then
    input_valid=true
  fi
done
