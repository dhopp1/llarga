# Change Log

### 0.0.7
### Added
* Added ability to change context prompt, switched to `condense_plus_context` chat mode.

### 0.0.6
### Added
* Added dockerfiles and database export and import functionality.

### 0.0.5
### Fixed
* Moved context window to only be handled on an LLM-level.
* Fixed chat memory limit overflowing the context window leading the model to stop answering.

### 0.0.4
### Added
* Added Google News support for generation of a corpus.

### 0.0.3
### Changed
* Made model parameters persistent per user between sessions.

### 0.0.2
### Changed
* Split the LLM from the user sesssion. All users share the same LLM, unlimited users.

### 0.0.1
### Added
* Initial release, depends on local_rag_llm==0.0.11. Separate LLMs for every user. Number of users restricted by amount of VRAM.