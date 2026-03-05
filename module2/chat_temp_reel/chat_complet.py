import tornado.websocket
import tornado.web
import tornado.ioloop
import json
from datetime import datetime
from collections import defaultdict

# ============================================================
# Gestion des salles et des clients
# ============================================================

class GestionnaireSalles:
    """Gestionnaire central de toutes les salles de chat."""

    def __init__(self):
        # {nom_salle: {websocket: info_client}}
        self.salles = defaultdict(dict)
        self.historique = defaultdict(list)  # 50 derniers messages par salle

    def rejoindre(self, salle, ws, pseudo):
        self.salles[salle][ws] = {"pseudo": pseudo, "connexion": datetime.now().isoformat()}

    def quitter(self, ws):
        """Retirer un client de toutes les salles."""
        for salle in list(self.salles.keys()):
            if ws in self.salles[salle]:
                pseudo = self.salles[salle].pop(ws)["pseudo"]
                return salle, pseudo
        return None, None

    def diffuser_salle(self, salle, message, exclu=None):
        """Envoyer un message à tous les membres d'une salle."""
        msg_json = json.dumps(message)
        a_supprimer = set()

        for ws in self.salles[salle]:
            if ws is exclu:
                continue
            try:
                ws.write_message(msg_json)
            except Exception:
                a_supprimer.add(ws)

        for ws in a_supprimer:
            self.salles[salle].pop(ws, None)

    def ajouter_historique(self, salle, message):
        self.historique[salle].append(message)
        if len(self.historique[salle]) > 50:
            self.historique[salle].pop(0)  # Garder 50 messages max

    def membres(self, salle):
        return [info["pseudo"] for info in self.salles[salle].values()]

    def liste_salles(self):
        return {s: len(m) for s, m in self.salles.items() if m}


# Instance globale du gestionnaire
gestionnaire = GestionnaireSalles()

# ============================================================
# Handler WebSocket du chat
# ============================================================

class ChatSalleHandler(tornado.websocket.WebSocketHandler):

    def check_origin(self, origin):
        return True

    def open(self):
        """Nouvelle connexion -- le client doit s'authentifier."""
        self.pseudo = None
        self.salle = None
        self.write_message(json.dumps({
            "type": "connexion",
            "message": "Bienvenue ! Envoyez votre pseudo et la salle pour rejoindre."
        }))

    def on_message(self, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            self.write_message(json.dumps({"type": "erreur", "message": "JSON invalide"}))
            return

        type_msg = data.get("type", "")

        if type_msg == "rejoindre":
            self._rejoindre_salle(data)
        elif type_msg == "message":
            self._envoyer_message(data)
        elif type_msg == "liste_salles":
            self._lister_salles()
        elif type_msg == "historique":
            self._envoyer_historique()

    def _rejoindre_salle(self, data):
        pseudo = data.get("pseudo", "").strip()
        salle = data.get("salle", "general").strip()

        if not pseudo:
            self.write_message(json.dumps({"type": "erreur", "message": "Pseudo requis"}))
            return

        self.pseudo = pseudo
        self.salle = salle

        gestionnaire.rejoindre(salle, self, pseudo)

        # Confirmer l'entrée
        self.write_message(json.dumps({
            "type": "rejoint",
            "salle": salle,
            "pseudo": pseudo,
            "membres": gestionnaire.membres(salle),
            "historique": gestionnaire.historique[salle][-20:]
        }))

        # Annoncer aux autres membres
        gestionnaire.diffuser_salle(salle, {
            "type": "systeme",
            "message": f"{pseudo} a rejoint la salle {salle}",
            "membres": gestionnaire.membres(salle),
            "heure": datetime.now().strftime("%H:%M:%S")
        }, exclu=self)

    def _envoyer_message(self, data):
        if not self.pseudo or not self.salle:
            self.write_message(json.dumps({"type": "erreur", "message": "Rejoignez une salle d'abord"}))
            return

        texte = data.get("texte", "").strip()
        if not texte:
            return

        msg = {
            "type": "message",
            "pseudo": self.pseudo,
            "texte": texte,
            "salle": self.salle,
            "heure": datetime.now().strftime("%H:%M:%S")
        }

        gestionnaire.ajouter_historique(self.salle, msg)
        gestionnaire.diffuser_salle(self.salle, msg)

    def _lister_salles(self):
        self.write_message(json.dumps({
            "type": "salles",
            "salles": gestionnaire.liste_salles()
        }))

    def _envoyer_historique(self):
        self.write_message(json.dumps({
            "type": "historique",
            "messages": gestionnaire.historique.get(self.salle, [])
        }))

    def on_close(self):
        if self.pseudo and self.salle:
            salle, pseudo = gestionnaire.quitter(self)
            if salle:
                gestionnaire.diffuser_salle(salle, {
                    "type": "systeme",
                    "message": f"{pseudo} a quitté la salle",
                    "membres": gestionnaire.membres(salle),
                    "heure": datetime.now().strftime("%H:%M:%S")
                })


# ============================================================
# API REST pour lister les salles
# ============================================================

class SallesAPIHandler(tornado.web.RequestHandler):
    def get(self):
        self.write({"salles": gestionnaire.liste_salles()})


# ============================================================
# Application
# ============================================================

def make_app():
    return tornado.web.Application([
        (r"/ws/chat", ChatSalleHandler),
        (r"/api/salles", SallesAPIHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {"path": ".", "default_filename": "index.html"}),
    ], debug=True)


if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("Serveur de chat démarré sur ws://localhost:8888/ws/chat")
    tornado.ioloop.IOLoop.current().start()