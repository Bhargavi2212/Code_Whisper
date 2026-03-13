@echo off
REM Use the same Python for pip and running (avoids ModuleNotFoundError).
python -m pip install pyautogui fastapi uvicorn pydantic --quiet
python click_agent.py
