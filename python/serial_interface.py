import serial
import time
import struct
from typing import List, Optional, Tuple, Dict, Any

class CharaDevice:
    def __init__(self, port, baudrate=115200):
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=2,  # Shorter timeout for interactive use
            write_timeout=2,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            rtscts=False,  # Disable hardware flow control
            dsrdtr=False   # Disable hardware flow control
        )
        time.sleep(0.5)  # Give device time to initialize
        self.version = None
        self.company = None
        self.device = None
        self.chipset = None
        self.key_count = None
        self.layer_count = 3
        self.profile_count = 1
        
    def _send_raw(self, command: str) -> None:
        """Send raw command string"""
        cmd = command + '\r\n'
        print(f"Sending: {command}")
        self.serial.write(cmd.encode('ascii'))
        self.serial.flush()
        
    def _read_line(self, timeout: float = 2.0) -> Optional[str]:
        """Read a line with timeout"""
        start_time = time.time()
        buffer = b''
        
        while time.time() - start_time < timeout:
            if self.serial.in_waiting > 0:
                char = self.serial.read(1)
                if char == b'\n':
                    line = buffer.decode('ascii', errors='ignore').strip()
                    if line:
                        print(f"Received: {line}")
                        return line
                elif char == b'\r':
                    # Ignore CR, we'll catch the LF
                    continue
                else:
                    buffer += char
            time.sleep(0.001)
            
        return None
    
    def send_command(self, command_parts: List[str], timeout: float = 2.0) -> List[str]:
        """Send command and get response"""
        command = ' '.join(command_parts)
        self._send_raw(command)
        
        response = self._read_line(timeout)
        if response is None:
            return []
            
        # Parse response
        parts = response.split(' ')
        if len(parts) >= 1 and parts[0] == command_parts[0]:
            # For commands like "CML C1 0", check first two parts
            if len(command_parts) > 1 and len(parts) > 1:
                if parts[1] == command_parts[1]:
                    return parts[2:] if len(parts) > 2 else []
            else:
                return parts[1:] if len(parts) > 1 else []
        elif response.startswith("UKN"):
            print(f"Unknown command response: {response}")
            return []
            
        return []
    
    def init(self) -> bool:
        """Initialize connection and get device info"""
        try:
            # Get version
            version_response = self.send_command(['VERSION'])
            if version_response:
                self.version = ' '.join(version_response) if version_response else "Unknown"
            
            # Get device identity
            id_response = self.send_command(['ID'])
            if id_response and len(id_response) >= 3:
                self.company = id_response[0]
                self.device = id_response[1]
                self.chipset = id_response[2]
                
                # Set key count based on device
                key_counts = {
                    'ONE': 90, 'TWO': 90, 'LITE': 67, 'X': 256,
                    'ENGINE': 256, 'M4G': 90, 'M4GR': 90, 'T4G': 7, 'ZERO': 256
                }
                self.key_count = key_counts.get(self.device, 90)
                
                # Adjust for firmware versions
                if self.version and self._version_gte("2.2.0-beta.4"):
                    self.profile_count = 2 if self.chipset == "M0" else 3
                    
                if self.version and self._version_gte("2.2.0-beta.20"):
                    self.layer_count = 3 if self.chipset == "M0" else 4
                    
            return True
        except Exception as e:
            print(f"Initialization error: {e}")
            return False
    
    def _version_gte(self, target_version: str) -> bool:
        """Check if device version >= target_version (simplified)"""
        try:
            # Extract version numbers (ignore pre-release tags for comparison)
            current = self.version.split('-')[0].split('.')
            target = target_version.split('-')[0].split('.')
            
            for i in range(3):
                c = int(current[i]) if i < len(current) else 0
                t = int(target[i]) if i < len(target) else 0
                if c > t:
                    return True
                elif c < t:
                    return False
            return True  # Equal
        except:
            return False
    
    def get_chord_count(self) -> int:
        """Get number of chords stored on device"""
        response = self.send_command(['CML', 'C0'])
        if response and len(response) >= 1:
            try:
                return int(response[0])
            except ValueError:
                return 0
        return 0
    
    def get_ram_bytes_available(self) -> Optional[int]:
        """Get available RAM bytes"""
        response = self.send_command(['RAM'])
        if response and len(response) >= 1 and response[0] != "UKN":
            try:
                return int(response[0])
            except ValueError:
                pass
        return None
    
    def get_setting(self, profile: int, setting_id: int) -> Optional[int]:
        """Get a setting value"""
        # Setting ID format: id + profile * 0x100
        full_id = setting_id + profile * 0x100
        response = self.send_command(['VAR', 'B1', f"{full_id:X}"])
        if response and len(response) >= 2:
            # Response format: <value> <status>
            if response[1] == "0":  # Status 0 = success
                try:
                    return int(response[0])
                except ValueError:
                    pass
        return None
    
    def get_chord(self, index: int) -> Dict[str, Any]:
        """Get chord at specified index"""
        response = self.send_command(['CML', 'C1', str(index)])
        if response and len(response) >= 2:
            actions_hex = response[0]
            phrase_hex = response[1] if len(response) > 1 else ""
            
            # Handle remaining phrase parts if any
            for part in response[2:]:
                phrase_hex += part
            
            return {
                'index': index,
                'actions_hex': actions_hex,
                'actions': self._parse_chord_actions(actions_hex),
                'phrase_hex': phrase_hex,
                'phrase': self._parse_phrase(phrase_hex)
            }
        return {
            'index': index,
            'actions_hex': '',
            'actions': [],
            'phrase_hex': '',
            'phrase': []
        }
    
    def _parse_chord_actions(self, hex_str: str) -> List[int]:
        """Parse chord actions from hex string"""
        try:
            value = int(hex_str, 16)
            actions = []
            for i in range(12):
                action = (value >> (i * 10)) & 0x3FF
                if action != 0:
                    # Actions are stored in reverse order
                    actions.append(action)
            # Return in original order
            return actions[::-1]
        except ValueError:
            return []
    
    def _parse_phrase(self, hex_str: str) -> List[int]:
        """Parse phrase from hex string"""
        try:
            # Simple parser - actual compression may be more complex
            phrase = []
            i = 0
            while i < len(hex_str):
                # Try to parse variable length hex numbers
                # Look for 2, 3, or 4 character hex numbers
                for length in [4, 3, 2]:
                    if i + length <= len(hex_str):
                        try:
                            val = int(hex_str[i:i+length], 16)
                            phrase.append(val)
                            i += length
                            break
                        except ValueError:
                            continue
                else:
                    # If no valid hex found, skip one character
                    i += 1
            return phrase
        except Exception as e:
            print(f"Error parsing phrase: {e}")
            return []
    
    def query_key(self, timeout: float = None) -> Optional[int]:
        """Query current key state (real-time)"""
        try:
            if timeout is None:
                # For interactive query, we don't want to timeout
                self.serial.timeout = None
            else:
                self.serial.timeout = timeout
                
            self._send_raw("QRY KEY")
            response = self._read_line(timeout if timeout else 10.0)
            
            if response:
                parts = response.split(' ')
                if len(parts) >= 3 and parts[0] == "QRY" and parts[1] == "KEY":
                    try:
                        return int(parts[2])
                    except ValueError:
                        pass
            return None
        finally:
            # Reset timeout
            self.serial.timeout = 2.0
    
    def get_device_info(self) -> Dict[str, Any]:
        """Get comprehensive device info"""
        return {
            'port': self.serial.port,
            'baudrate': self.serial.baudrate,
            'version': self.version,
            'company': self.company,
            'device': self.device,
            'chipset': self.chipset,
            'key_count': self.key_count,
            'layer_count': self.layer_count,
            'profile_count': self.profile_count,
            'is_connected': self.serial.is_open
        }
    
    def test_commands(self) -> Dict[str, Any]:
        """Test various commands and return results"""
        results = {}
        
        # Test basic commands
        results['version'] = self.version
        results['identity'] = f"{self.company} {self.device} {self.chipset}"
        
        # Test chord commands
        chord_count = self.get_chord_count()
        results['chord_count'] = chord_count
        
        # Test RAM command
        ram = self.get_ram_bytes_available()
        results['ram_available'] = ram
        
        # Test a few settings
        settings = {}
        for setting_id in [0x10, 0x20, 0x30]:  # Common settings
            val = self.get_setting(0, setting_id)
            if val is not None:
                settings[f"0x{setting_id:02X}"] = val
        results['settings'] = settings
        
        # Get a sample chord
        if chord_count > 0:
            chord = self.get_chord(0)
            results['sample_chord'] = {
                'index': 0,
                'actions_hex': chord['actions_hex'],
                'actions': chord['actions'],
                'phrase_hex': chord['phrase_hex'],
                'phrase': [hex(x) for x in chord['phrase']]
            }
        
        return results
    
    def close(self):
        """Close serial connection"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            print("Connection closed")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def main():
    """Main function to test device communication"""
    port = '/dev/ttyACM0'  # Change this to your actual port
    
    print(f"Connecting to device at {port}...")
    device = CharaDevice(port)
    
    try:
        # Initialize device
        if device.init():
            info = device.get_device_info()
            print("\n" + "="*50)
            print("DEVICE INFORMATION")
            print("="*50)
            for key, value in info.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
            
            print("\n" + "="*50)
            print("SYSTEM STATUS")
            print("="*50)
            
            # Get detailed info
            chord_count = device.get_chord_count()
            print(f"Stored Chords: {chord_count}")
            
            ram = device.get_ram_bytes_available()
            if ram is not None:
                print(f"RAM Available: {ram} bytes")
            else:
                print("RAM Available: Command not supported")
            
            # Try to read some settings
            print("\nSettings:")
            setting_ids = [0x10, 0x20, 0x30, 0x40, 0x50]
            for sid in setting_ids:
                val = device.get_setting(0, sid)
                if val is not None:
                    print(f"  Setting 0x{sid:02X}: {val}")
            
            # Get a few chords
            print("\n" + "="*50)
            print("SAMPLE CHORDS")
            print("="*50)
            
            if chord_count > 0:
                # Get first 3 chords
                for i in range(min(3, chord_count)):
                    chord = device.get_chord(i)
                    print(f"\nChord #{i}:")
                    print(f"  Actions HEX: {chord['actions_hex']}")
                    print(f"  Actions: {chord['actions']}")
                    print(f"  Phrase HEX: {chord['phrase_hex']}")
                    print(f"  Phrase: {[hex(x) for x in chord['phrase']]}")
            
            # Test real-time key query
            print("\n" + "="*50)
            print("REAL-TIME KEY TEST")
            print("="*50)
            print("Press any key on the device (Ctrl+C to stop)...")
            
            try:
                for i in range(20):  # Try for 20 readings
                    key_state = device.query_key(timeout=0.5)
                    if key_state is not None:
                        if key_state != 0:
                            print(f"  Key pressed: {key_state} (0x{key_state:X})")
                        # else:
                        #     print(f"  No key pressed")
                    else:
                        print(f"  No response")
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\nStopped by user")
            
            # Run comprehensive test
            print("\n" + "="*50)
            print("COMPREHENSIVE TEST")
            print("="*50)
            results = device.test_commands()
            
            print(f"\nSummary:")
            print(f"- Firmware: {results.get('version', 'Unknown')}")
            print(f"- Device: {results.get('identity', 'Unknown')}")
            print(f"- Chords: {results.get('chord_count', 0)}")
            print(f"- RAM: {results.get('ram_available', 'N/A')}")
            
            if 'settings' in results and results['settings']:
                print(f"- Settings read: {len(results['settings'])}")
            
        else:
            print("Failed to initialize device")
            
    except serial.SerialException as e:
        print(f"Serial port error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if device is connected")
        print("2. Check port name (try: ls /dev/tty*)")
        print("3. Check permissions: sudo chmod 666 /dev/ttyACM0")
        print("4. Try different baud rates (9600, 57600, 115200)")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
    finally:
        device.close()


def quick_test():
    """Quick test to verify basic communication"""
    port = '/dev/ttyACM0'
    
    try:
        device = CharaDevice(port)
        print(f"Testing connection to {port}...")
        
        # Quick version check
        response = device.send_command(['VERSION'])
        if response:
            print(f"✓ Version: {' '.join(response)}")
        else:
            print("✗ No response to VERSION command")
        
        # Quick ID check
        response = device.send_command(['ID'])
        if response and len(response) >= 3:
            print(f"✓ Device: {' '.join(response)}")
        else:
            print("✗ No response to ID command")
        
        device.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")


if __name__ == "__main__":
    # Run quick test first
    quick_test()
    
    # Uncomment to run full test
    print("\n" + "="*50)
    print("RUNNING FULL TEST")
    print("="*50)
    main()
