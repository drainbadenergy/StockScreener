@echo off
REM Launch the EOD Breakout Screener dashboard (works when streamlit is not on PATH).
cd /d "%~dp0"
python -m streamlit run app\streamlit_app.py %*
