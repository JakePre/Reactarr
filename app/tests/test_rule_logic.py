import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add app directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import handle_sonarr_rule, check_rule

class TestRuleLogic(unittest.TestCase):

    @patch('app.sonarr_api_request')
    def test_preview_imported_episodes(self, mock_sonarr_api):
        # Mock Series response
        mock_sonarr_api.side_effect = [
            # First call: get series
            [
                {'id': 1, 'title': 'Test Series 1'},
                {'id': 2, 'title': 'Test Series 2'}
            ],
            # Second call: get episodes for Series 1
            [
                {'id': 101, 'seriesId': 1, 'title': 'Episode 1', 'hasFile': True, 'monitored': True},
                {'id': 102, 'seriesId': 1, 'title': 'Episode 2', 'hasFile': False, 'monitored': True}
            ],
            # Third call: get episodes for Series 2
            [
                {'id': 201, 'seriesId': 2, 'title': 'Episode 3', 'hasFile': True, 'monitored': True}
            ],
             # Mock tag/profile calls which might happen inside handle_sonarr_rule
            [], # tags
            []  # profiles
        ]

        rule = {
            'mediaType': 'episode',
            'eventType': 'imported',
            'action': 'delete' # Action doesn't matter for preview
        }

        # This should return episodes 101 and 201 because they have files (simulating imported)
        affected_items = handle_sonarr_rule(rule, dry_run=True)
        
        # Verify we got episodes, not series
        self.assertTrue(len(affected_items) > 0, "Should have found affected items")
        self.assertEqual(affected_items[0]['title'], 'Episode 1')
        self.assertEqual(len(affected_items), 2) # Episode 1 and 3

    def test_check_rule_imported_library_item(self):
        rule = {'eventType': 'imported'}
        
        # Case 1: Library item with file
        item_with_file = {'hasFile': True, 'monitored': True}
        self.assertTrue(check_rule(rule, item_with_file, {}))

        # Case 2: Library item without file
        item_no_file = {'hasFile': False, 'monitored': True}
        self.assertFalse(check_rule(rule, item_no_file, {}))

    def test_check_rule_enhanced_fields(self):
        # Base item
        item = {
            'hasFile': True,
            'monitored': True,
            'mediaInfo': {
                'videoCodec': 'h264',
                'audioCodec': 'ac3',
                'resolution': '1080p'
            },
            'quality': {
                'quality': {
                    'resolution': 1080
                }
            },
            'size': 1024 * 1024 * 500 # 500 MB
        }

        # Test Video Codec
        self.assertTrue(check_rule({'eventType': 'imported', 'videoCodec': 'h264'}, item, {}))
        self.assertFalse(check_rule({'eventType': 'imported', 'videoCodec': 'hevc'}, item, {}))

        # Test Audio Codec
        self.assertTrue(check_rule({'eventType': 'imported', 'audioCodec': 'ac3'}, item, {}))
        self.assertFalse(check_rule({'eventType': 'imported', 'audioCodec': 'aac'}, item, {}))

        # Test Resolution
        self.assertTrue(check_rule({'eventType': 'imported', 'resolution': '1080'}, item, {}))
        self.assertFalse(check_rule({'eventType': 'imported', 'resolution': '720'}, item, {}))

        # Test Size
        self.assertTrue(check_rule({'eventType': 'imported', 'minSize': '100'}, item, {})) # > 100MB
        self.assertTrue(check_rule({'eventType': 'imported', 'maxSize': '1000'}, item, {})) # < 1000MB
        self.assertFalse(check_rule({'eventType': 'imported', 'minSize': '600'}, item, {})) # > 600MB (fail)
        self.assertFalse(check_rule({'eventType': 'imported', 'maxSize': '400'}, item, {})) # < 400MB (fail)

    @patch('app.sonarr_api_request')
    def test_search_action(self, mock_sonarr_api):
        # Test that search action triggers EpisodeSearch
        rule = {
            'mediaType': 'episode',
            'eventType': 'missing',
            'action': 'search'
        }
        item = {'id': 123, 'episodeId': 456, 'title': 'Test Episode', 'status': 'pending'}
        
        # Mock check_rule to return True (we can just call handle_sonarr_rule directly with dry_run=False)
        # But handle_sonarr_rule calls check_rule internally. 
        # Let's mock check_rule or just ensure our item passes check_rule.
        # For 'missing' event, check_rule expects monitored=True (default behavior for missing?)
        # Let's use a simpler event type or ensure item matches.
        
        # Let's use 'grabbed' event for simplicity in matching
        rule['eventType'] = 'grabbed'
        item['status'] = 'pending'
        
        # We need to mock the queue response for handle_sonarr_rule to find our item
        mock_sonarr_api.side_effect = [
            {'records': [item]}, # queue response
            [], # tags
            [], # profiles
            {} # command response
        ]
        
        handle_sonarr_rule(rule, dry_run=False)
        
        # Verify that the last call was the command
        # We expect 4 calls: queue, tags, profiles, command
        self.assertEqual(mock_sonarr_api.call_count, 4)
        
        # Check the arguments of the last call (the command)
        args, kwargs = mock_sonarr_api.call_args
        self.assertEqual(args[0], 'command')
        self.assertEqual(kwargs['method'], 'POST')
        self.assertEqual(kwargs['json']['name'], 'EpisodeSearch')
        self.assertEqual(kwargs['json']['episodeIds'], [456])

if __name__ == '__main__':
    unittest.main()
