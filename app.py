from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

@app.route('/assistant', methods=['POST'])
def assistant():
    data = request.json or {}
    query = data.get('query', '').lower()
    
    classe = data.get('classe', '').strip().upper()
    scuola = data.get('scuola', '').strip().upper()
    token = data.get('token', '').strip()
    
    compiti_list = []
    debug_info = ""
    
    if any(k in query for k in ["compiti", "didup", "programmazione", "esercizi"]):
        if not token:
            reply = "Sessione Argo non autenticata."
            return jsonify({'reply': reply, 'compiti': []})
            
        try:
            session = requests.Session()
            clean_token = token.replace('Bearer', '').replace('bearer', '').strip()
            
            # Usiamo l'endpoint alternativo della bacheca o della agenda se la dashboard fa i capricci
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Authorization': f'Bearer {clean_token}',
                'x-auth-token': clean_token,
                'x-cod-min': scuola,
                'os-type': 'WEB',
                'argo-client-version': '4.2.3',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            }
            
            # Proviamo l'endpoint specifico dei compiti assegnati
            url = f"https://didattica.portaleargo.it/famiglia/api/compiti/compiti"
            
            res = session.get(url, headers=headers, timeout=15)
            
            if res.status_code == 200:
                decoded = res.json()
                items = decoded if isinstance(decoded, list) else decoded.get('dati', []) or decoded.get('compitiAssegnati', [])
                for item in items:
                    compiti_list.append({
                        'data': item.get('datGiorno') or item.get('datCompito') or '',
                        'materia': item.get('desMateria') or 'Materia',
                        'descrizione': item.get('desCompito') or 'Compito',
                    })
            else:
                debug_info = f"HTTP {res.status_code}"
                
        except Exception as e:
            debug_info = f"Eccezione: {str(e)}"

    if "compiti" in query or "didup" in query:
        if compiti_list:
            testo_compiti = ", ".join([f"{c['materia']}: {c['descrizione']}" for c in compiti_list[:3]])
            reply = f"Ho trovato {len(compiti_list)} compiti su didUP. Tra cui: {testo_compiti}"
        else:
            reply = f"Nessun compito trovato. Errore API Argo ({debug_info})"
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
