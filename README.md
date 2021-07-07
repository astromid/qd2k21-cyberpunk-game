# qd2k21-cyberpunk-game

Code for cyberpunk game (first) related code, performed at Quantum Dot 2021

Expose WSL server to local network:
```powershell
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=172.20.97.225
netsh advfirewall add rule name="Streamlit Port 8501" dir=in action=allow protocol=TCP localport=8501

netsh advfirewall firewall delete rule name="Streamlit Port 8501"
netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0
```
