from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

@app.route('/assistant', methods=['POST'])
def assistant():
    data = request.json or {}
    query = data.get('query', '').lower()
    classe = data.get('classe', '3C')
    
    scuola = data.get('scuola', '')
    user = data.get('user', '')
    passwd = data.get('pass', '')
    
    compiti_list = []
    
    if any(k in query for k in ["compiti", "didup", "programmazione", "esercizi"]):
        if scuola and user and passwd:
            try:
                session = requests.Session()
                
                # 1. Login su Argo
                login_res = session.post(
                    "https://portaleargo.it/auth/sso/api/login",
                    headers={
                        'Content-Type': 'application/json',
                        'X-Codice-Scuola': scuola.upper(),
                    },
                    json={
                        "codiceScuola": scuola.upper(),
                        "username": user,
                        "password": passwd,
                    },
                    timeout=10
                )
                
                if login_res.status_code == 200:
                    login_data = login_res.json()
                    token = (
                        login_data.get('token') or 
                        login_data.get('tokenAuth') or 
                        login_data.get('accessToken') or 
                        login_data.get('tokenKey') or ''
                    )
                    
                    headers = {
                        'X-Codice-Scuola': scuola.upper(),
                        'Accept': 'application/json, text/plain, */*',
                    }
                    if token:
                        headers['X-Auth-Token'] = token
                        headers['Authorization'] = f'Bearer {token}'
                        
                    now = datetime.date.today()
                    future = now + datetime.timedelta(days=14)
                    
                    compiti_res = session.get(
                        f"https://portaleargo.it/famiglia/api/rest/v2/compiti-assegnati?da={now.isoformat()}&a={future.isoformat()}",
                        headers=headers,
                        timeout=10
                    )
                    
                    if compiti_res.status_code == 200:
                        decoded = compiti_res.json()
                        items = []
                        if isinstance(decoded, dict):
                            items = decoded.get('dati', []) or decoded.get('compiti', [])
                        elif isinstance(decoded, list):
                            items = decoded
                            
                        for item in items:
                            compiti_list.append({
                                'data': item.get('datGiorno') or item.get('datCompito', ''),
                                'materia': item.get('desMateria') or item.get('materia', ''),
                                'descrizione': item.get('desCompito') or item.get('compito') or item.get('annotazioni', ''),
                            })
            except Exception as e:
                print(f"Errore connessione Argo: {e}")

    if "compiti" in query or "didup" in query:
        if compiti_list:
            testo_compiti = ", ".join([f"{c['materia']}: {c['descrizione']}" for c in compiti_list[:3]])
            reply = f"Ho trovato {len(compiti_list)} compiti su didUP. Tra cui: {testo_compiti}"
        else:
            reply = f"Non ho trovato compiti registrati su didUP nei prossimi giorni."
    else:
        reply = f"Ho ricevuto il tuo comando per la classe {classe}: {query}"

    return jsonify({
        'reply': reply,
        'compiti': compiti_list
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)