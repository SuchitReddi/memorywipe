#!/bin/bash

#Only the functions defined before the case statement can be called inside it.

# Checks if a certain program is installed or not
#read -p "Enter the application name: " app #If you want to take the user input
chk_install() {
  local command_name="$1"

  # Check if the command is already installed
  if command -v "$command_name" >/dev/null 2>&1; then
    echo "$command_name is installed."
    return 0
  else
    echo "$command_name is not installed"
    return 1
  fi

  #Using in other functions:
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

# Check partition
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

# Extraction - mtd devices using nanddump
ins_nanddump() {
  echo
  echo "Checking for existing installation..."

  app="nanddump"
  chk_install "$app"
  install_result=$?
  #echo "Install result is: $install_result"

  if [ $install_result -eq 0 ]; then
    echo "nanddump...Check!"
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

# Sanitization - devices with ATA SECURE ERASE enabled using hdparm
#ata_hdparm() {
#
#}

# Installing veracrypt
ins_veracrypt() {
  app="veracrypt"
  echo "Checking for existing $app installation..."
  #echo "Install result is: $install_result"
  #chk_install "$app" > /dev/null 2>&1  # If you want to suppress the output
  chk_install "$app"
  install_result=$?

  if [ $install_result -eq 0 ]; then
    echo "Veracrypt...Check!"
  else
    echo "Installing Veracrypt..."
    sudo wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-console-1.26.7-Debian-11-armhf.deb --connect-timeout=5 -c -P ./veracrypt >/dev/null 2>&1 && sudo apt install ./veracrypt/veracrypt-console-1.26.7-Debian-11-armhf.deb -y >/dev/null 2>&1

    echo "Checking for successful installation"
    app="veracrypt"
    chk_install "$app"
    install_result=$?
    if [ $install_result -eq 0 ]; then
      echo "Veracrypt...Check!"
    else
      echo "Veracrypt installation failed!! Install manually."
      echo
      echo "Note: "
      echo

      echo "If it did not work for you, change the version and architecture according to your device and os..."
      echo
      echo "For example, raspberry pi uses armhf architecture. So, the required command is:"
      echo "sudo wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-console-1.26.7-Debian-11-armhf.deb --connect-timeout=5 -c -P ./veracrypt && sudo apt install ./veracrypt/veracrypt-console-1.26.7-Debian-11-armhf.deb -y"
    fi
  fi
  #sudo -S <<(echo "pass")>> wget https://launchpad.net/veracrypt/trunk/1.26.7/+download/veracrypt-1.26.7-setup.tar.bz2 --connect-timeout=5 -c -P ./veracrypt/ && sudo -S <<(echo "pass")>> tar xjf ./veracrypt/veracrypt* -C ./veracrypt
}

chk_unmount() {
  #ISSUE: If the target partition /dev/sda1 is already unmounted, and the user gives sda1 as input, it does not work as intended.
  #sda1 will not be found in the /proc/mounts, so it says successfully unmounted, but sda1 is not even a block device.
  #read -p "Enter your device's partition (/dev/sdb1): " partition
  echo "Unmounting the partition..."
  #sudo umount $partition

  # Check if the partition is unmounted
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

chk_encrypted() {
  command=$(lsblk -f $partition)
  # Check if there is a partition with the name "veracrypt"
  if echo "$command" | grep -q "veracrypt"; then
    return 0
  else
    return 1
  fi
}

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
	  read -p "So set a very strong random password: " strongp
	  sudo veracrypt -t -c --volume-type=normal $partition --encryption=aes --hash=sha-512 --filesystem=ntfs -p $strongp --pim=0 -k "" --random-source=/dev/urandom
	  sudo veracrypt -t $partition /mnt/ -p $strongp --pim=0 -k "" --protect-hidden=no
	  sudo veracrypt -d $partition #Unmount the veracrypt volume
      else
	echo "Invalid input. Please give either 'm' or 'a'" 
      fi
    fi
  fi
}

format_disk() {
  echo "Formatting $partition..."
  if chk_unmount; then
    read -p "Set device name: " name
    sudo mkfs.ntfs -L $name $partition
    echo "Formatted $partition"
    return 0
  else
    echo "Make sure the disk is unmounted!"
    return 1
  fi
}

mount_disk() {
  echo "Mounting $partition at /mnt/$name"
  sudo mkdir /mnt/$name > /dev/null 2>&1
  sudo mount $partition /mnt/$name/
  echo "Finished mounting!"
}

# Sanitization - any device that supports encryption tools (Veracrypt - most compatible)
crypt_erase() {
  echo "Starting Cryptographic Erasure using Veracrypt..."
  ins_veracrypt
  echo

  echo "WARNING: This process is irreversible. Create necessary backups if required (You may use the extraction module for this)."
  echo
  echo "NOTE: Cryptographic erasure on Flash Storage partitions may not be effective. Perform it on the whole disk."
  echo "If there are multiple partitions in the device, format them into one single partition, and then perform erasure."
  list_partitions

  #Setting a value for partition (/dev/sdb1) to erase
  echo
  echo "Select /dev/sdb, if you want to erase the whole drive, partitioned as sdb1, sdb2, ..., sdb#"
  read -p "Enter your device's partition (/dev/sdb1): " partition
  if chk_unmount; then
    echo
  else
    echo "Unmounting failed!! Please unmount manually before proceeding"
    echo
    return 1
  fi
  
  # Start veracrypt encryption (manual or automatic)
  veracrypt_encrypt
  echo
  echo "Finished encrypting $partition"
  
  format_disk
  echo
  mount_disk 
  
  echo "Cryptographic Erasure procedure completed successfully!"
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
    echo "[1] Cryptographic Erasure"
    echo "[2] ATA Secure Erase (hdparm)"
    echo "[3] Diskpart"

    read -p "Select your wiping method: " wipe
    echo
    case $wipe in
    1)
      echo "You selected Cryptographic Erasure"
      # Code for option 1
      crypt_erase
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
