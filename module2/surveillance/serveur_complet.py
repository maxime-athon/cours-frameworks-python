import tornado.web
import tornado.ioloop
import tornado.websocket
import aiosqlite
import asyncio
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "surveillance.db")

# -----------------------------
# Étape 1 : Initialisation BDD
# -----------------------------
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS alertes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niveau TEXT NOT NULL, -- "warning" | "critique"
            message TEXT NOT NULL,
            capteur TEXT NOT NULL,
            valeur REAL,
            timestamp TEXT NOT NULL
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS capteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL, -- "temperature" | "humidite" | "pression"
            unite TEXT,
            actif INTEGER DEFAULT 1
        )
        """)
        await db.commit()
        print(f"[DB] Base de données initialisée : {DB_PATH}")


# -----------------------------
# Étape 2 : WebSocket Handler
# -----------------------------
class CapteurWSHandler(tornado.websocket.WebSocketHandler):
    """ WebSocket pour recevoir et diffuser les données de capteurs. """
    clients = set()

    def check_origin(self, origin):
        return True

    def open(self):
        CapteurWSHandler.clients.add(self)
        self.write_message(json.dumps({
            "type": "connecte",
            "clients": len(CapteurWSHandler.clients)
        }))
        print(f"[WS] Nouveau client. Total : {len(CapteurWSHandler.clients)}")

    async def on_message(self, message):
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        if data.get("type") == "mesure":
            valeur = float(data.get("valeur", 0))
            raw_seuil = data.get("seuil")
            seuil = float(raw_seuil) if raw_seuil is not None else float("inf")

            mesure = {
                "type": "mesure",
                "capteur": data["capteur"],
                "valeur": valeur,
                "unite": data.get("unite", ""),
                "heure": datetime.now().isoformat()
            }

            # Vérification du seuil
            if valeur > seuil:
                alerte = {
                    "type": "alerte",
                    "niveau": "warning",
                    "message": f"Seuil dépassé sur {data['capteur']} ({valeur} > {seuil})",
                    "capteur": data["capteur"],
                    "valeur": valeur,
                    "heure": datetime.now().isoformat()
                }
                # Persistance en BDD
                async with aiosqlite.connect(DB_PATH) as db:
                    await db.execute(
                        "INSERT INTO alertes (niveau, message, capteur, valeur, timestamp) VALUES (?, ?, ?, ?, ?)",
                        (alerte["niveau"], alerte["message"], alerte["capteur"], alerte["valeur"], alerte["heure"])
                    )
                    await db.commit()
                # Diffusion de l’alerte
                await self._diffuser(alerte)

            # Diffusion de la mesure brute
            await self._diffuser(mesure)

    def on_close(self):
        CapteurWSHandler.clients.discard(self)
        print(f"[WS] Client déconnecté. Restants : {len(CapteurWSHandler.clients)}")

    @classmethod
    async def _diffuser(cls, data):
        msg = json.dumps(data)
        inactifs = set()
        for client in cls.clients:
            try:
                client.write_message(msg)
            except Exception:
                inactifs.add(client)
        cls.clients -= inactifs


# -----------------------------
# Étape 3 : API REST Alertes
# -----------------------------
class AlertesHandler(tornado.web.RequestHandler):
    """ GET /api/alertes?limite=50&niveau=warning """
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")

    async def get(self):
        limite = int(self.get_argument("limite", "50"))
        niveau = self.get_argument("niveau", None)

        query = "SELECT * FROM alertes"
        params = []
        if niveau:
            query += " WHERE niveau = ?"
            params.append(niveau)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limite)

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()

        alertes = [dict(r) for r in rows]
        self.write({"alertes": alertes, "total": len(alertes)})


# -----------------------------
# Étape 4 : Application & Main
# -----------------------------
def make_app():
    return tornado.web.Application([
        (r"/ws/capteurs", CapteurWSHandler),
        (r"/api/alertes", AlertesHandler),
        (r"/(.*)", tornado.web.StaticFileHandler, {
            "path": os.path.dirname(os.path.abspath(__file__)),
            "default_filename": "client.html"
        }),
    ], debug=True)


async def main():
    await init_db()
    app = make_app()
    app.listen(8888)
    print("Serveur de surveillance sur http://localhost:8888")
    print(" WebSocket : ws://localhost:8888/ws/capteurs")
    print(" API REST : GET http://localhost:8888/api/alertes")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())