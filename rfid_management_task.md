# Task: RFID Management App Enhancement

## Description
Develop a comprehensive RFID/NFC management application to streamline the creation, editing, and maintenance of interactive signage tags. This involves enhancing the existing `TagCreator.py` utility into a robust tool suitable for non-technical museum staff, ensuring reliable tag-to-video mapping and asset management.

## TODO
- [ ] UI/UX Refinement
  - [ ] Implement a more modern and intuitive interface (potentially switching from Tkinter to a web-based dashboard or a modern Python GUI framework like CustomTkinter)
  - [ ] Add a "Tag Gallery" view to browse and search all registered tags without needing to scan them
  - [ ] Include video previews within the management interface
- [ ] Robust Asset Management
  - [ ] Implement automatic video transcoding/optimization to ensure compatibility with the signage player
  - [ ] Add validation for file formats and resolutions
  - [ ] Implement a "Clean Up" utility to remove orphaned video files in `artifacts/`
- [ ] Hardware & Connectivity
  - [ ] Improve NFC reader stability and connection retry logic
  - [ ] Add support for multiple NFC reader models (e.g., ACR122U) via `pyscard`
  - [ ] Implement a "Test Scan" mode to verify tag IDs without affecting the database
- [ ] System Integration
  - [ ] Sync the `testdata.json` automatically with the interactive signage backend
  - [ ] Add logging for tag creation and modification events
  - [ ] Implement a backup/restore feature for the tag database and assets

## Acceptance Criteria
- [ ] Users can create, edit, and delete tags with associated videos for multiple languages (EN, ES, TE)
- [ ] Changes in the management app are immediately reflected in the interactive signage frontend
- [ ] The app handles "broken tag replacement" by easily re-assigning existing organ data to new physical tags
- [ ] Orphaned assets are identified and can be safely removed by the user
- [ ] The interface provides visual confirmation of video paths and tag IDs
- [ ] The application remains responsive during long-running tasks like file copying or reader polling
