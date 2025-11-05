"""Storage and change detection for litter data."""

import json
import os
from typing import List, Dict, Any, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class LitterStorage:
    """Handles storage and change detection for litter data."""

    def __init__(self, storage_file: str = "data/previous_litters.json"):
        """
        Initialize storage.

        Args:
            storage_file: Path to the JSON file for storing previous litter data
        """
        self.storage_file = storage_file
        self._ensure_storage_exists()

    def _ensure_storage_exists(self):
        """Ensure the storage directory and file exist."""
        os.makedirs(os.path.dirname(self.storage_file), exist_ok=True)
        if not os.path.exists(self.storage_file):
            self._write_data({'litters': {}, 'last_updated': None})

    def _read_data(self) -> Dict[str, Any]:
        """Read data from storage file."""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading storage file: {str(e)}")
            return {'litters': {}, 'last_updated': None}

    def _write_data(self, data: Dict[str, Any]):
        """Write data to storage file."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error writing storage file: {str(e)}")

    def get_previous_litter_ids(self) -> Set[str]:
        """
        Get set of previously seen litter IDs.

        Returns:
            Set of litter IDs
        """
        data = self._read_data()
        return set(data.get('litters', {}).keys())

    def detect_new_litters(self, current_litters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect new litters by comparing with previously stored litters.

        Args:
            current_litters: List of current litter dictionaries

        Returns:
            List of new litter dictionaries
        """
        previous_ids = self.get_previous_litter_ids()
        new_litters = []

        for litter in current_litters:
            litter_id = litter.get('id')
            if litter_id and litter_id not in previous_ids:
                new_litters.append(litter)

        return new_litters

    def update_litters(self, litters: List[Dict[str, Any]]):
        """
        Update stored litters with current data.

        Args:
            litters: List of current litter dictionaries
        """
        data = self._read_data()

        # Convert list to dictionary keyed by ID
        litter_dict = {litter['id']: litter for litter in litters if 'id' in litter}

        # Update with new data
        data['litters'].update(litter_dict)
        data['last_updated'] = datetime.now().isoformat()

        self._write_data(data)
        logger.info(f"Updated storage with {len(litter_dict)} litters")

    def get_all_litters(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all stored litters.

        Returns:
            Dictionary of litters keyed by ID
        """
        data = self._read_data()
        return data.get('litters', {})

    def cleanup_old_litters(self, keep_ids: Set[str]):
        """
        Remove litters that are no longer present on websites.

        Args:
            keep_ids: Set of litter IDs to keep
        """
        data = self._read_data()
        litters = data.get('litters', {})

        # Remove litters not in keep_ids
        removed_count = 0
        for litter_id in list(litters.keys()):
            if litter_id not in keep_ids:
                del litters[litter_id]
                removed_count += 1

        if removed_count > 0:
            data['litters'] = litters
            data['last_updated'] = datetime.now().isoformat()
            self._write_data(data)
            logger.info(f"Removed {removed_count} old litters from storage")
