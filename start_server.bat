@echo off
echo Starting Enterprise RAG Chatbot Server...

start "Backend" cmd /k "cd /d C:\Users\srush\Downloads\enterprise-rag-chatbot\enterprise-rag-chatbot\backend && C:\Users\srush\Downloads\enterprise-rag-chatbot\enterprise-rag-chatbot\.venv\Scripts\python.exe -m uvicorn app:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

start "Frontend" cmd /k "cd /d C:\Users\srush\Downloads\enterprise-rag-chatbot\enterprise-rag-chatbot\frontend && python -m http.server 8001"

echo.
echo Server started!
echo Clients can connect at: http://192.168.1.4:8001/login.html
echo.
pause
