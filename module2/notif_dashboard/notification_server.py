import tornado.web
import tornado.ioloop
import asyncio
import json
from datetime import datetime
from collections import defaultdict
import uuid

class BaseSSEHandler(tornado.web.RequestHandler):
    """Handler de base pour la logique commune SSE."""
    def initialize(self):
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")
        self.set_header("Access-Control-Allow-Origin", "*")

    def envoyer_sse(self, event, data):
        """Formate et envoie un événement SSE."""
        try:
            self.write(f"event: {event}\n")
            self.write(f"data: {json.dumps(data)}\n\n")
            self.flush()
        except tornado.iostream.StreamClosedError:
            # Le client s'est déconnecté, on ne fait rien.
            pass

class GestionnaireNotifications:
    """Gestionnaire central des abonnés et des notifications."""

    def __init__(self):
        # {user_id: [NotificationsSSEHandler, ...]}
        self.abonnes = defaultdict(list)
        # File d'attente : notifs arrivées hors connexion
        self.en_attente = defaultdict(list)

    def abonner(self, user_id, handler):
        """Enregistre un handler SSE et rejoue les notifications manquées."""
        self.abonnes[user_id].append(handler)
        for notif in self.en_attente.get(user_id, []):
            handler.envoyer_sse("notification", notif)
        self.en_attente.pop(user_id, None)

    def desabonner(self, user_id, handler):
        """Désabonne un handler."""
        if user_id in self.abonnes and handler in self.abonnes[user_id]:
            self.abonnes[user_id].remove(handler)
            if not self.abonnes[user_id]:
                del self.abonnes[user_id]

    def notifier(self, user_id, notification):
        """Envoyer une notification à un utilisateur spécifique."""
        handlers = self.abonnes.get(user_id)
        if handlers:
            for h in handlers:
                h.envoyer_sse("notification", notification)
        else:
            # Utilisateur hors ligne : Stocker pour plus tard
            self.en_attente[user_id].append(notification)

    def notifier_tous(self, notification):
        """Diffuser une notification à tous les abonnés connectés."""
        for user_id in list(self.abonnes.keys()):
            handlers = self.abonnes.get(user_id, [])
            for h in handlers:
                h.envoyer_sse("notification", notification)

# Instance globale
gestionnaire_notifs = GestionnaireNotifications()

class NotificationsSSEHandler(BaseSSEHandler):
    """
    Client SSE par utilisateur: GET /sse/notifs/<user_id>
    Connexion HTTP persistante ; le serveur pousse les événements.
    """
    def initialize(self):
        super().initialize()
        self.user_id = None

    async def get(self, user_id):
        self.user_id = user_id
        gestionnaire_notifs.abonner(user_id, self)

        # Événement de confirmation de connexion
        self.envoyer_sse("connexion", {
            "user_id": user_id,
            "message": "Abonnement aux notifications actif"
        })

        try:
            while True:
                # Heartbeat toutes les 15s pour garder la connexion vivante
                await asyncio.sleep(15)
                self.envoyer_sse("ping", {"heure": datetime.now().isoformat()})
        except asyncio.CancelledError:
            # Le client s'est déconnecté
            pass

    def on_connection_close(self):
        if self.user_id:
            gestionnaire_notifs.desabonner(self.user_id, self)

class EnvoyerNotifHandler(tornado.web.RequestHandler):
    """
    API REST : POST /api/notifier
    Payload JSON : {user_id?, titre, message, niveau}
    niveau: "info", "succes", "warning", "erreur"
    """
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
        self.set_header('Access-Control-Allow-Methods', 'POST, OPTIONS')

    def options(self):
        self.set_status(204)
        self.finish()

    async def post(self):
        try:
            data = json.loads(self.request.body)
        except json.JSONDecodeError:
            self.set_status(400)
            self.write({"erreur": "JSON invalide"})
            return

        notif = {
            "id": str(uuid.uuid4()),
            "titre": data.get("titre", "Notification"),
            "message": data.get("message", ""),
            "niveau": data.get("niveau", "info"),  # info | succes | warning | erreur
            "heure": datetime.now().isoformat()
        }

        user_id = data.get("user_id")
        if user_id:
            gestionnaire_notifs.notifier(str(user_id), notif)
            self.write({"message": f"Notification envoyée à {user_id}"})
        else:
            gestionnaire_notifs.notifier_tous(notif)
            self.write({"message": "Notification diffusée à tous"})

class TableauBordHandler(BaseSSEHandler):
    """
    Tableau de bord SSE : GET /sse/dashboard
    Envoie des métriques toutes les 3 secondes.
    """
    abonnes = set()  # Tous les clients dashboard connectés

    async def get(self):
        TableauBordHandler.abonnes.add(self)
        self.envoyer_sse("connexion", {"message": "Dashboard connecté"})

        try:
            while True:
                metriques = await self._collecter_metriques()
                self.envoyer_sse("metriques", metriques)
                await asyncio.sleep(3)
        except asyncio.CancelledError:
            pass

    def on_connection_close(self):
        TableauBordHandler.abonnes.discard(self)

    async def _collecter_metriques(self):
        """Collecter les métriques (simulation ; remplacer par psutil en prod)."""
        import random
        active_users = {uid for uid, handlers in gestionnaire_notifs.abonnes.items() if handlers}
        return {
            "cpu": round(random.uniform(10, 90), 1),
            "memoire": round(random.uniform(40, 80), 1),
            "connexions": len(active_users),
            "requetes": random.randint(100, 500),
            "heure": datetime.now().isoformat()
        }

def make_app():
    return tornado.web.Application([
        (r"/sse/notifs/(.+)", NotificationsSSEHandler),
        (r"/sse/dashboard", TableauBordHandler),
        (r"/api/notifier", EnvoyerNotifHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {
            "path": ".",
            "default_filename": "dashboard.html"
        }),
    ], debug=True)

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print("Serveur Tornado démarré sur http://localhost:8888")
    print(" SSE notifications : http://localhost:8888/sse/notifs/<user_id>")
    print(" SSE dashboard : http://localhost:8888/sse/dashboard")
    print(" API notifier : POST http://localhost:8888/api/notifier")
    tornado.ioloop.IOLoop.current().start()