import unittest
import os
import json
import shutil
import time
from TagCreator import TagManager

# Setup paths for testing (using temporary test file)
TEST_DIR = "test_assets_temp"
TEST_JSON = os.path.join(TEST_DIR, "testdata.json")
TEST_ARTIFACTS = os.path.join(TEST_DIR, "artifacts")

class TestTagManager(unittest.TestCase):
    def setUp(self):
        # Create test directory structure
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)
        os.makedirs(TEST_ARTIFACTS)
        
        # Create dummy video file
        with open("dummy.mp4", "w") as f:
            f.write("dummy content")

        # Initial JSON data
        initial_data = [] # Start empty
        with open(TEST_JSON, 'w') as f:
            json.dump(initial_data, f)
            
        self.tm = TagManager(json_path=TEST_JSON, artifacts_dir=TEST_ARTIFACTS)

    def tearDown(self):
        if os.path.exists(TEST_DIR):
            shutil.rmtree(TEST_DIR)
        if os.path.exists("dummy.mp4"):
            os.remove("dummy.mp4")

    def test_create_tag(self):
        video_paths = {"en": "dummy.mp4", "es": "dummy.mp4", "te": "dummy.mp4"}
        new_tag = self.tm.create_tag("123", "Heart", video_paths)
        
        # Verify JSON
        self.assertEqual(len(self.tm.data), 1)
        self.assertEqual(self.tm.data[0]['id'], "123")
        self.assertEqual(self.tm.data[0]['name'], "Heart")
        
        # Verify Files
        expected_path = os.path.join(TEST_ARTIFACTS, "Heart", "en.mp4")
        self.assertTrue(os.path.exists(expected_path))

    def test_update_tag_rename(self):
        # Setup existing
        video_paths = {"en": "dummy.mp4", "es": "dummy.mp4", "te": None}
        self.tm.create_tag("123", "Heart", video_paths)
        
        # Rename
        new_paths = {"en": None, "es": None, "te": None} # No file changes
        self.tm.update_tag_files("123", "Lung", new_paths)
        
        # Verify JSON
        tag = self.tm.get_tag_by_id("123")
        self.assertEqual(tag['name'], "Lung")
        self.assertTrue("artifacts/Lung/" in tag['path']['en'])
        
        # Verify Folder Rename
        self.assertTrue(os.path.exists(os.path.join(TEST_ARTIFACTS, "Lung")))
        self.assertFalse(os.path.exists(os.path.join(TEST_ARTIFACTS, "Heart")))

    def test_replace_broken_tag(self):
        # Setup existing organ with old ID
        video_paths = {"en": "dummy.mp4", "es": None, "te": None}
        self.tm.create_tag("123", "Brain", video_paths)
        
        # Replace ID
        success = self.tm.replace_broken_tag("Brain", "999")
        self.assertTrue(success)
        
        # Verify
        tag = self.tm.get_tag_by_name("Brain")
        self.assertEqual(tag['id'], "999")

    def test_delete_tag(self):
        self.tm.create_tag("123", "ToBeDeleted", {"en": None, "es": None, "te": None})
        self.tm.delete_tag("123")
        
        tag = self.tm.get_tag_by_id("123")
        self.assertIsNone(tag)

if __name__ == '__main__':
    unittest.main()
