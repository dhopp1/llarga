# Change Log

### 0.0.3
### Changed
* Made model parameters persistent per user between sessions.

### 0.0.2
### Changed
* Split the LLM from the user sesssion. All users share the same LLM, unlimited users.

### 0.0.1
### Added
* Initial release, depends on local_rag_llm==0.0.11. Separate LLMs for every user. Number of users restricted by amount of VRAM.