@echo off
TITLE Lanzador Automatizado - Sistema Matinal 2.0
cd /d "C:\Proyectos\MATINAL ONLINE"

echo [1/2] Levantando servidor local de Streamlit...
start "Streamlit_Matinal" /min cmd /c "streamlit run app.py"

:: Pausa de 5 segundos para garantizar la inicializacion del puerto 8501
timeout /t 5 /nobreak > nul

echo [2/2] Generando tunel cifrado de Cloudflare...
:: Utiliza el tunel rapido temporal. Reemplazar por 'cloudflared tunnel run matinal-online' si se migra a dominio propio.
start "Cloudflare_Tunnel" /min cmd /c "cloudflared tunnel --url http://localhost:8501"

exit