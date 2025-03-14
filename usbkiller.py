import time
import psutil
import subprocess
import platform
import logging
import os

# Configuration
TIMEOUT_SECONDS = 600  # 10 minutes (adjust as needed)
LOG_FILE = "usb_killer.log"
WHITELIST_FILE = "usb_whitelist.txt" # File containing whitelisted serial numbers
LOGGING_LEVEL = logging.INFO  # Set default log level

# Logging Setup
logging.basicConfig(filename=LOG_FILE, level=LOGGING_LEVEL,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_whitelist(whitelist_file):
    """Loads the list of whitelisted USB serial numbers from a file."""
    try:
        with open(whitelist_file, "r") as f:
            whitelist = [line.strip() for line in f]  # Read each line, remove whitespace
        logging.info(f"Whitelist loaded: {whitelist}")
        return whitelist
    except FileNotFoundError:
        logging.warning(f"Whitelist file not found: {whitelist_file}. Starting with an empty whitelist.")
        return []
    except Exception as e:
        logging.error(f"Error loading whitelist: {e}")
        return []

def get_usb_serial(drive_path):
    """
    Gets the serial number of a USB drive (OS-specific).
    This is where you would implement OS-specific logic to retrieve the serial.
    This example returns "UNKNOWN" - REPLACE THIS WITH ACTUAL IMPLEMENTATION.
    """
    os_name = platform.system()
    try:
        if os_name == "Windows":
            # Example using wmic (requires admin privileges)
            try:
                command = ["wmic", "diskdrive", "where", f"Index='{drive_path[0]}'", "get", "SerialNumber", "/value"] #get the drive index and serial number
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                output = result.stdout.strip()
                for line in output.splitlines():
                    if "SerialNumber=" in line:
                        serial_number = line.split("=")[1].strip()
                        logging.info(f"Serial Number of {drive_path} is {serial_number}")
                        return serial_number

                return "UNKNOWN" #If can't get the serial number, return UNKNOWN to prevent problems
            except Exception as e:
                logging.error(f"Error getting serial on Windows: {e}")
                return "UNKNOWN"
        elif os_name == "Linux":
             #This is very dependent on the specific system
             try:
                 command = ["udevadm", "info", "--name", drive_path]  # Replace with the correct device node
                 result = subprocess.run(command, capture_output=True, text=True, check=True)
                 output = result.stdout.strip()
                 for line in output.splitlines():
                     if "ID_SERIAL=" in line:
                        serial_number = line.split("=")[1].strip()
                        logging.info(f"Serial Number of {drive_path} is {serial_number}")
                        return serial_number
                 return "UNKNOWN"

             except Exception as e:
                 logging.error(f"Error getting serial on Linux: {e}")
                 return "UNKNOWN"

        else:
            logging.warning(f"Unsupported OS, can't get serial for {drive_path}")
            return "UNKNOWN" #If the OS is not suppported return UNKNOWN
    except Exception as e:
       logging.error(f"An unexpected error occurred: {e}")
       return "UNKNOWN"


def get_removable_drives():
    """Detects removable USB drives (Windows and Linux compatible)."""
    drives = []
    for partition in psutil.disk_partitions():
        if 'removable' in partition.opts:  # Windows
            drives.append(partition.mountpoint)
        elif partition.fstype and partition.mountpoint.startswith('/media'):  # Linux heuristic
            drives.append(partition.mountpoint)
    return drives

def eject_usb_drive(drive_path, whitelist):
    """Ejects a USB drive unless it's whitelisted."""
    serial_number = get_usb_serial(drive_path)

    if serial_number in whitelist:
        logging.info(f"Drive {drive_path} with serial {serial_number} is whitelisted, skipping ejection.")
        return False  # Do not eject

    os_name = platform.system()
    logging.info(f"Attempting to eject drive: {drive_path} (Serial: {serial_number}) on {os_name}")

    try:
        if os_name == "Windows":
            command = ["powershell", "Dismount-Volume", "-DriveLetter", drive_path[0] + ":"]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            logging.info(f"Eject command result: {result.stdout} {result.stderr}")

        elif os_name == "Linux":
            command = ["umount", drive_path]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            logging.info(f"Eject command result: {result.stdout} {result.stderr}")
        else:
            logging.error(f"Unsupported operating system: {os_name}")
            return False

        logging.info(f"Successfully ejected {drive_path}")
        return True

    except subprocess.CalledProcessError as e:
        logging.error(f"Error ejecting {drive_path}: {e.stderr}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return False

def main():
    """Main function to monitor and eject USB drives after a timeout."""
    try:
        logging.info("USB Auto-Kill Switch started.")
        whitelist = load_whitelist(WHITELIST_FILE)
        initial_drives = get_removable_drives()
        logging.info(f"Initial drives: {initial_drives}")

        while True:
            time.sleep(TIMEOUT_SECONDS)

            current_drives = get_removable_drives()
            new_drives = [drive for drive in current_drives if drive not in initial_drives]

            if new_drives:
                logging.info(f"New drives detected: {new_drives}")
                for drive in new_drives:
                    if eject_usb_drive(drive, whitelist):
                        logging.info(f"Successfully ejected: {drive}")
                    else:
                        logging.warning(f"Failed to eject or whitelisted: {drive}")
                initial_drives = get_removable_drives()  # Refresh drives

            else:
                logging.info("No new drives detected.")

    except KeyboardInterrupt:
        logging.info("USB Auto-Kill Switch stopped by user.")
    except Exception as e:
        logging.error(f"An unexpected error occurred in main loop: {e}")
    finally:
        logging.info("USB Auto-Kill Switch exiting.")

if __name__ == "__main__":
    main()
