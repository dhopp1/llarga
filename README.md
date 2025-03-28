# Llarga
Llarga stands for 'Local Large language RAG Application'. A streamlit application for interfacing with a local RAG LLM.

## Set up
- install instructions

## User management
- The app has a password, which you can set by creating a `.streamlit/` directory in the base directory of the app, with a `secrets.toml` file inside containing `password = "desired_password"`
- You can change various theme options by creating a `.streamlit/config.toml` file, containin e.g.:

```
[theme]
primaryColor="#5b92E5"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F0F2F6"
```