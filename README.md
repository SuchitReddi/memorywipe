<b>This README is for users, not developers! Developers should check CONTRIBUTING.md, and DEVELOPMENT.md.</b>  
You can find the report and presentation of this project in "docs" folder.
# Memory Wipe
A linux command line utility for storage sanitization. Developed for IoT devices with shell access,
keeping modern flash storages like SSDs in mind.

## Warning
<b>BE VERY CAREFUL WHILE RUNNING THIS SCRIPT.</b><br> 
This is a data sanitization tool, which aims to make data unrecoverable. 
Please don't start a sanitization method without knowing what it does. 
Make necessary backups before using the tool.

## Usage
This tool can be used on any linux device. But it was mostly tested on a Raspberry Pi 4B.
<ol>
  <li>Clone the repository: <code>git clone https://github.com/suchitreddi/memorywipe.git</code></li>
  <li>Run the script: <code>bash memorywipe.sh</code></li>
</ol>

## Forensic Issues of IoT devices using NAND Flash Memory (Research)

<b>Working of SSD</b><br>
Flash memory used in SSDs is cheap with high read/write speeds. This makes it ideal for usage in IoT devices.<br>
However it's working is different from the old magnetic disks used in HDDs. If you edit a file on a HDD, it is actually deleted and overwritten.<br>
But in SSDs, the data can be deleted only in blocks but not as individual cells. If you edit a few bits in an SSD, you have to delete the entire block just to edit those few bits.<br>
This results in a lot of program and erase (PE) cycles. SSDs have limited PE cycles. So, overwriting is done differently.<br>
When a file is edited, the controller marks the old block as invalid and writes the new data to a different location.<br>
When the system asks for the updated file, it gives the new location. But the old data is still present in the old location.<br>

<b>Forensic Issues</b><br>
When you delete a file, the controller marks the file pointer as invalid without actually deleting it.<br>
The actual deletion happens when the SSD is idle, in the background. Processes like garbage collection, TRIM, and wear leveling are involved.<br>
Once a block is marked invalid, it is inaccessible to the operating system. You have to hack the flash controller to access it.<br>
There are methods requiring sophisticated hardware and expertise to access unmanaged blocks.<br>
Unlike HDDs, write blockers have no impact on stopping wear levelling.<br>
So theoretically if you leave your device idle for a long time, the SSD itself should delete your data. But there is no fixed time after which the file is actually erased.<br>

<b>Flash memory problems</b><br>
On HDDs, writing random or (0/1)s to the entire disk is enough to make the data unrecoverable. Degaussing and physical destruction are used to make the drive unusable.<br>
So, it is fairly easy to securely sanitize HDDs. But in SSDs, it is very hard but possible to access these unmanaged/invalid blocks.<br>

<b>Sanitization Methods</b><br>
These methods should work on flash storages, but most importantly on IoT devices.<br>
-->ATA Secure Erase<br>
This is set of commands will activate manufacturer provided firmware functions to erase the drive.<br>
It is the most secure method to sanitize SSDs. But it is not supported by all manufacturers.<br>
And it was also found by some researchers that many manufacturers does not implement sanitization correctly.<br>
-->Cryptographic Wiping<br>
The entire drive is encrypted using VeraCrypt. It was chosen because of its wide compatibility range, including ARM devices (Raspberry Pi).<br>
The encrypted drive, along with the key is overwritten with a pass of random values and zeroes. The drive is then formatted into a usable filesystem format.<br>
-->Automatic Wiping<br>
This option checks compatibility of the device with different sanitization methods in the tool and apply the most compatible one.<br>

<b>Verification</b><br>
To verify if data is still accessible, I used an open source forensics tool called "Autopsy".<br>
There are better tools like Cellebrite, and Magnet Axiom, but they are neither open source, nor cheap.<br>
I plan on adding a terminal based forensic tool like PhotoRec, and Sleuth Kit's Scalpel. This allows verification on the same device on which sanitization takes place.<br>

<b>Future Prospects</b><br>
To be 100% certain of data sanitization, a disk read at physical level is required. It should either be done using a costly chip reader like PC-3000,<br>
or a custom FPGA board connected to the chip using a TSOP DIP48 adapter.<br>

## Disclaimer
I am not responsible for any data lost intentionally or unintentionally. I have given necessary warnings.<br>
How the tool is utilized, is the sole responsiblity of the person(s) using this program.<br>

## Contact
Suchit Reddi: <a href="mailto:suchit20016+memorywipe@gmail.com" target="_blank" rel="noopener noreferrer nofollow">suchit20016+memorywipe@gmail.com</a>
