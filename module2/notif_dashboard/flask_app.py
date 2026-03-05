from flask import Flask, request, jsonify
import requests


app = Flask(__name__)

TORNADO_URL = "http://localhost:8888"

def notifier_utilisateur(user_id, titre, message, niveau="info"):
    """
    Envoyer une notification à un utilisateur via le serveur Tornado.
    Appelé depuis n'importe quelle route Flask.
    """
    try:
        resp = requests.post(
            f"{TORNADO_URL}/api/notifier",
            json={
                "user_id": str(user_id),
                "titre": titre,
                "message": message,
                "niveau": niveau
            },
            timeout=2  # Ne pas bloquer Flask si Tornado est indisponible
        )
        return resp.json()
    except requests.RequestException as e:
        print(f"Impossible de joindre Tornado : {e}")
        return None

# ---Exemple : notif après une commande---
@app.route("/commande", methods=["POST"])
def passer_commande():
    data = request.json
    user_id = data.get("user_id")
    produit = data.get("produit")

    # Logique métier Flask...
    # ...

    # Notifier l'utilisateur via Tornado SSE
    notifier_utilisateur(
        user_id,
        titre="Commande confirmée",
        message=f"Votre commande de {produit} a été validée.",
        niveau="succes"
    )
    return jsonify({"statut": "commande créée"})

# ---Exemple : alerte globale (broadcast)---
@app.route("/admin/alerte", methods=["POST"])
def envoyer_alerte():
    data = request.json
    # Pas de user_id -> diffusion à tous
    try:
        requests.post(f"{TORNADO_URL}/api/notifier", json={
            "titre": data.get("titre", "Alerte système"),
            "message": data.get("message", ""),
            "niveau": "warning"
        }, timeout=2)
        return jsonify({"statut": "alerte diffusée"})
    except requests.RequestException as e:
        print(f"Impossible de joindre Tornado : {e}")
        return jsonify({"statut": "erreur", "message": "Impossible de joindre le serveur de notification"}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)