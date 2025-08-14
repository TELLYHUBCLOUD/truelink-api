"""
Test script for the file upload server
"""
import requests
import os
from pathlib import Path

def test_upload_server():
    """Test the file upload functionality"""
    base_url = "http://localhost:3000"
    
    # Create a test file
    test_file_path = Path("test_file.txt")
    test_content = "This is a test file for upload testing."
    
    with open(test_file_path, "w") as f:
        f.write(test_content)
    
    try:
        # Test file upload
        print("Testing file upload...")
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_file.txt", f, "text/plain")}
            response = requests.post(f"{base_url}/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Upload successful!")
            print(f"   File URL: {result['url']}")
            print(f"   Filename: {result['filename']}")
            
            # Test file access
            print("\nTesting file access...")
            file_response = requests.get(result['url'])
            if file_response.status_code == 200:
                print("✅ File access successful!")
                print(f"   Content: {file_response.text}")
            else:
                print(f"❌ File access failed: {file_response.status_code}")
        else:
            print(f"❌ Upload failed: {response.status_code}")
            print(f"   Response: {response.text}")
        
        # Test file listing
        print("\nTesting file listing...")
        list_response = requests.get(f"{base_url}/files")
        if list_response.status_code == 200:
            files_data = list_response.json()
            print(f"✅ File listing successful!")
            print(f"   Found {files_data['count']} files")
        else:
            print(f"❌ File listing failed: {list_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure it's running on http://localhost:3000")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    finally:
        # Clean up test file
        if test_file_path.exists():
            test_file_path.unlink()

if __name__ == "__main__":
    test_upload_server()