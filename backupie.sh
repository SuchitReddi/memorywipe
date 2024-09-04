#!/bin/bash

# Declaring the variables
dev_path="/dev/mmcblk0"
back_path="/media/sherl0ck/dead/backups/"
backup_name="backup-$(date +%Y%m%d-%H%M%S).img"

set_dev_path() {
     echo
     echo "--- Setting device path ---"

     echo
     echo "If you are running backup, give path of device you want to backup"
     echo "If you are running restore, select device to write the backup image onto"
     echo "WARNING: If you are restoring, make sure you do it from some other device, and not this Pi"
     echo

     read -p "Enter your device path(/dev/mmcblk0)): " dev_path
}

set_back_path() {
     echo
     echo "--- Setting backup path ---"

     echo
     echo "If you are running backup, select where you want to store the backup"
     echo "If you are running restore, give location of backup image"
     echo

     read -p "Enter your backup path(/media/sherl0ck/dead/backups): " back_path
}

# Function for backup
backup() {

    set_dev_path
    set_back_path

    echo "Input path is : $dev_path"
    echo "Output path is : $back_path"

    echo
    echo "-----Starting backup-----"
    echo

    sudo dd bs=1M if="$dev_path" of="$back_path""$backup_name" status=progress

    echo
    echo "-----Finished backup, you can find the backup at $back_path$backup_name-----"
    echo
}

# Function for restore
restore() {

    set_back_path
    set_dev_path

    echo
    echo "-----Restoring from "$back_path" to "$dev_path"-----"
    echo

    # Restore logic
    sudo dd bs=1M if="$back_path" of="$dev_path" status=progress

    echo
    echo "-----Restored backup! Check whether the device is booting up-----"
    echo
}

# Main function starts here
main() {
    echo "Available actions: "
    echo "[1] Backup"
    echo "[2] Restore"
    
    read -p "Select one action: " action
    echo

    case $action in
        1)
            # Code for backup
            backup
            ;;
        2)
            # Code for restore
            restore
            ;;
        *)
            echo "-----Invalid option. Select 1 or 2-----"
            echo
            ;;
    esac
exit 0
}

# Call the main function
main
input_valid=false

while [ "$input_valid" = false ]; do
  if main; then
    input_valid=true
  fi
done
