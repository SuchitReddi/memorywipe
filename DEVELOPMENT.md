<b>Most of the code is easy to understand. A few comments will help understand how a particular objective is achieved.</b>  
I will give a brief explanation of important functions in this file.

# Format
- What does the function do?
- The logic behind the function.
- Issues and possible improvements for the function.

## <code>main()</code>
Let's start with the main function. As soon as you run the program, you will be asked to select an option from a list.  
If you select anything else, other than the provided options, a message to select valid options will be displayed.  

I used case statements to make this work. The basic template for that is:
```
echo "Available actions: "
  echo "[1] Option 1"
  echo "[2] Option 2"

  read -p "Select your option: " option
  echo
  case $option in
  1)
    # Code for option 1
    ;;
  2)
    # Code for option 2
    ;;
  *)
    # Invalid option. Select from 1, 2.
    main
    ;;
  esac
```
The option validation of this case statement is given below.
```
input_valid=false
while [ "$input_valid" = false ]; do
  if main; then
    input_valid=true
  fi
done
```
This input validation part was taken from bard, so I have no idea how that works. But without it, you won't see anything when the script runs!  

## <code>list_partitions()</code>
This function checks and installs the tool `lsblk`, and displays the connected storage devices.   
The user can select the mount point of the device on which they wish to execute operations like sanitization, extraction, or verification.

## <code>ins_tool_name()</code>
Each tool has a different installation process. But most tools can be downloaded using `sudo apt install $app`.  
This `$app` variable is used in many places, including the `chk_install()` function.

## <code>chk_install()</code>
This function checks and notifies the user if a required command line utility is installed.  

The logic used here is a simple version check command. Most linux tools show the version if a `-v` flag is given. If there is no output, then
the tool is not installed.  
But this logic fails with few tools that doesn't use `-v` or if the installation package name and executable package name are different for a tool.

For example, we use a command `nanddump`, in this program. But it is present in the installation package named `mtd-utils`. So, I gave below code in `ins_nanddump()` function:
```
app = "mtd-utils"
chk_install($app)
```
But the issue here is, the `chk_install()` function will check using `mtd-utils -v`. But we have to run `nanddump -v`, because `mtd-utils` is not an executable function. It will just return "command not found" error.

## <code>chk_umount()</code>
It is important to unmount a device before performing any operations. So, I wrote this function to check if the mount point selected by the user is unmounted or not.  

The logic used here is to check for the mount point in `/proc/mounts`. Any mounted device will appear there along with all it's partitions.  
So, for example if the user wants to sanitize a device mounted as `/dev/sda`, we will check if the device is unmounted beforehand.  
I introduced a variable `$partition` for this purpose. After taking `partition="/dev/sda"`, we will check if `$partition` is present in `/proc/mounts` by using:  
```
if grep -qs "$partition" /proc/mounts; then
```
The issue with this logic is that if the user gives a value that is not really a mount point, for example something like `/not/real`, then the function will check for it in `/proc/mounts`. It will not find it there, so it will be considered as successful unmounting.  

A better logic is needed for this function.

------------
### Cryptographic Wipe starts here
------------
## <code>veracrypt_encrypt()</code>
This function simply uses the veracrypt tool to provide the user with a manual/automatic encryption option.  
The user have to set the password which will be taken as `$strongp`, even in the automatic option.

## <code>chk_encrypted()</code>
This function checks if the user-selected partition is already encrypted. If it is, the encryption of that drive is skipped.

The logic is for the name veracrypt in `lsblk`. Because, if the partition is already encrypted, it will be shown as veracrypt in `lsblk`.

## <code>wipe_disk()</code>
This function overwrites the encrypted drive with a pass of random and zeroes each. Then formats the drive to `ntfs` once the user provides `$name`.  
```
sudo dd if=/dev/random of=$partition bs=1M status=progress # overwriting with random values using dd
sudo dd if=/dev/zero of=$partition bs=1M status=progress > /dev/null 2>&1 # To suppress stdout

read -p "Set device name: " name
sudo mkfs.ntfs -L $name $partition # Format to ntfs filesystem
```

The `mkfs.ntfs` function only formats into ntfs filesystem. Improvements should be made here to format in other filesystems as per user requirement.

## <code>mount_disk()</code>
This function simply creates a folder with the name the user provides for the sanitized drive, and mounts it at that location.  
`sudo mount $partition /media/$name`

## <code>crypt_wipe()</code>
This function just combines all the above individual steps of the cryptographic wipe process into a single function.  
This will be used in the main function to make it less cluttered.

------------
### Cryptographic Wipe ends here
------------
### Secure Erase processes start here
------------
<b>TODO: These processes should be updated here in the same way cryptographic wipe was added</b>  
Work in Progress...

## <code>chk_compat_hdparm()</code>
This function checks if the selected storage device is compatible with hdparm commands.

------------
### Secure Erase processes end here
------------