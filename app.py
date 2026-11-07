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
    token = data.get('token', '').strip() # Riceviamo il token di sessione direttamente dall'app
    
    compiti_list = []
    debug_info = ""
    
    if any(k in query for k in ["compiti", "didup", "programmazione", "esercizi"]):
        if not token:
            reply = "Sessione Argo non autenticata. Effettua l'accesso nell'app per sincronizzare i compiti."
            return jsonify({'reply': reply, 'compiti': []})
            
        try:
            session = requests.Session()
            
            # Intestazioni con il token di sessione autenticato dall'utente
            headers = {
                'X-Codice-Scuola': scuola,
                'Accept': 'application/json, text/plain, */*',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Authorization': f'Bearer {token}',
                'X-Auth-Token': token
            }
            
            now = datetime.date.today()
            past = now - datetime.timedelta(days=7)
            future = now + datetime.timedelta(days=14)
            
            # Chiamata diretta all'endpoint dei compiti di Argo
            compiti_res = session.get(
                f"https://www.portaleargo.it/famiglia/api/rest/v2/compiti-assegnati?da={past.isoformat()}&a={future.isoformat()}",
                headers=headers,
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
                        'data': item.get('datGiorno') or item.get('datCompito') or '',
                        'materia': item.get('desMateria') or item.get('materia') or 'Materia',
                        'descrizione': item.get('desCompito') or item.get('compito') or 'Compito',
                    })
            else:
                debug_info = f"Errore API Argo (HTTP {compiti_res.status_code})"
                
        except Exception as e:
            debug_info = f"Eccezione di rete: {str(e)}"

    if "compiti" in query or "didup" in query:
        if compiti_list:
            testo_compiti = ", ".join([f"{c['materia']}: {c['descrizione']}" for c in compiti_list[:3]])
            reply = f"Ho trovato {len(compiti_list)} compiti su didUP. Tra cui: {testo_compiti}"
        else:
            reply = f"Nessun compito trovato o sessione scaduta. {debug_info}"
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
