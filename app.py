from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

@app.route('/assistant', methods=['POST'])
def assistant():
    data = request.json or {}
    query = data.get('query', '').lower()
    
    classe = data.get('classe', '').strip().upper()
    scuola = data.get('scuola', '').strip().upper()
    user = data.get('user', '').strip()
    passwd = data.get('pass', '').strip()
    
    compiti_list = []
    debug_info = ""
    
    if any(k in query for k in ["compiti", "didup", "programmazione", "esercizi"]):
        if not scuola or not user or not passwd:
            reply = "Credenziali didUP non trovate. Inserisci Scuola, Utente e Password nel menu Impostazioni dell'app."
            return jsonify({'reply': reply, 'compiti': []})
            
        try:
            session = requests.Session()
            
            base_headers = {
                'Content-Type': 'application/json',
                'X-Codice-Scuola': scuola,
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Mobile Safari/537.36',
                'Host': 'www.portaleargo.it'
            }
            
            # Proviamo l'endpoint di autenticazione alternativo di Argo DidUp
            login_urls = [
                "https://www.portaleargo.it/auth/sso/api/login",
                "https://www.portaleargo.it/famiglia/api/rest/login",
                "https://www.portaleargo.it/api/v1/login"
            ]
            
            login_res = None
            for url in login_urls:
                try:
                    res = session.post(
                        url,
                        headers=base_headers,
                        json={
                            "codiceScuola": scuola,
                            "username": user,
                            "password": passwd,
                        },
                        timeout=10
                    )
                    if res.status_code != 404:
                        login_res = res
                        break
                except:
                    continue
            
            if login_res is None or login_res.status_code != 200:
                status_code = login_res.status_code if login_res else "404/Timeout"
                debug_info = f"Login fallito su tutti gli endpoint (Ultimo HTTP {status_code})"
            else:
                login_data = login_res.json()
                token = (
                    login_data.get('token') or 
                    login_data.get('tokenAuth') or 
                    login_data.get('accessToken') or 
                    login_data.get('tokenKey') or ''
                )
                
                auth_headers = {
                    'X-Codice-Scuola': scuola,
                    'Accept': 'application/json, text/plain, */*',
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Mobile)',
                    'Host': 'www.portaleargo.it'
                }
                if token:
                    auth_headers['X-Auth-Token'] = token
                    auth_headers['Authorization'] = f'Bearer {token}'
                    
                now = datetime.date.today()
                past = now - datetime.timedelta(days=15)
                future = now + datetime.timedelta(days=30)
                
                compiti_res = session.get(
                    f"https://www.portaleargo.it/famiglia/api/rest/v2/compiti-assegnati?da={past.isoformat()}&a={future.isoformat()}",
                    headers=auth_headers,
                    timeout=15
                )
                
                if compiti_res.status_code == 200:
                    decoded = compiti_res.json()
                    items = []
                    if isinstance(decoded, dict):
                        items = decoded.get('dati', []) or decoded.get('compiti', []) or decoded.get('compitiAssegnati', [])
                    elif isinstance(decoded, list):
                        items = decoded
                        
                    for item in items:
                        compiti_list.append({
                            'data': item.get('datGiorno') or item.get('datCompito') or item.get('datAnno', ''),
                            'materia': item.get('desMateria') or item.get('materia') or item.get('desMateriaPratica', ''),
                            'descrizione': item.get('desCompito') or item.get('compito') or item.get('annotazioni', ''),
                        })
                else:
                    debug_info = f"HTTP {compiti_res.status_code} su recupero compiti"
        except Exception as e:
            debug_info = f"Eccezione: {str(e)}"

    if "compiti" in query or "didup" in query:
        if compiti_list:
            testo_compiti = ", ".join([f"{c['materia']}: {c['descrizione']}" for c in compiti_list[:3]])
            reply = f"Ho trovato {len(compiti_list)} compiti su didUP. Tra cui: {testo_compiti}"
        else:
            reply = f"Nessun compito trovato. {debug_info}"
    else:
        info_classe = f" per la classe {classe}" if classe else ""
        reply = f"Comando ricevuto{info_classe}: {query}"

    return jsonify({
        'reply': reply,
        'compiti': compiti_list
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
