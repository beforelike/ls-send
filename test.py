"""
LS Send - Test Script

Test the discovery and transfer modules.
"""

import sys
import time
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent))

from shared import generate_device_id, DeviceInfo
from shared.discovery import DeviceDiscovery
from shared.transfer import TransferServer, FileSender


def test_discovery():
    """Test device discovery"""
    print("=" * 50)
    print("Testing Device Discovery")
    print("=" * 50)
    
    device_id = generate_device_id()
    device_name = f"Test-{device_id}"
    
    discovery = DeviceDiscovery(device_id, device_name, "test")
    
    devices_found = []
    
    def on_found(device: DeviceInfo):
        print(f"\n✓ Device found: {device.device_name} @ {device.ip}")
        devices_found.append(device)
    
    def on_lost(device_id: str):
        print(f"\n✗ Device lost: {device_id}")
    
    discovery.set_callbacks(on_found, on_lost)
    
    print(f"\nStarting discovery as '{device_name}'...")
    discovery.start()
    
    print("Listening for 10 seconds (send 'q' to quit early)...")
    
    try:
        for i in range(10):
            time.sleep(1)
            print(f".", end="", flush=True)
    except KeyboardInterrupt:
        pass
    
    print(f"\n\nDiscovery complete!")
    print(f"Devices found: {len(devices_found)}")
    
    for device in devices_found:
        print(f"  - {device.device_name} ({device.ip}:{device.port})")
    
    discovery.stop()
    print("\nDiscovery stopped.")
    
    return len(devices_found) > 0


def test_transfer_server():
    """Test transfer server"""
    print("\n" + "=" * 50)
    print("Testing Transfer Server")
    print("=" * 50)
    
    device_id = generate_device_id()
    
    server = TransferServer(device_id, save_dir="./test_received")
    
    def on_request(request):
        print(f"\n✓ Transfer request from {request.sender_name}")
        print(f"  Files: {len(request.files)}")
        session_id = server.create_session(request)
        return True, session_id, "Accepted"
    
    def on_progress(session_id, bytes_recv, total, filename):
        percent = int((bytes_recv / total) * 100) if total > 0 else 0
        print(f"  Progress: {percent}%")
    
    def on_complete(session_id):
        print(f"\n✓ Transfer complete: {session_id}")
    
    server.set_callbacks(
        on_transfer_request=on_request,
        on_progress=on_progress,
        on_complete=on_complete
    )
    
    print(f"\nStarting transfer server on port 53531...")
    server.start()
    
    print("Server running for 5 seconds...")
    time.sleep(5)
    
    server.stop()
    print("\nServer stopped.")
    
    return True


def test_file_hash():
    """Test file hash calculation"""
    print("\n" + "=" * 50)
    print("Testing File Hash")
    print("=" * 50)
    
    from shared import calculate_file_hash
    
    # Create a test file
    test_file = Path("./test_hash.txt")
    test_content = b"Hello, LS Send!"
    
    test_file.write_bytes(test_content)
    
    hash1 = calculate_file_hash(str(test_file))
    hash2 = calculate_file_hash(str(test_file))
    
    print(f"File: {test_file}")
    print(f"Content: {test_content.decode()}")
    print(f"Hash 1: {hash1}")
    print(f"Hash 2: {hash2}")
    print(f"Hashes match: {hash1 == hash2}")
    
    # Clean up
    test_file.unlink()
    
    return hash1 == hash2


def main():
    """Run all tests"""
    print("\nLS Send - Test Suite")
    print("=" * 50)
    
    results = []
    
    # Test 1: File hash
    print("\n[Test 1] File Hash Calculation")
    results.append(("File Hash", test_file_hash()))
    
    # Test 2: Transfer server
    print("\n[Test 2] Transfer Server")
    results.append(("Transfer Server", test_transfer_server()))
    
    # Test 3: Discovery (requires other devices on network)
    print("\n[Test 3] Device Discovery")
    print("(This test requires other LS Send instances on the network)")
    results.append(("Discovery", test_discovery()))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print(f"\nOverall: {'✓ All tests passed!' if all_passed else '✗ Some tests failed'}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
