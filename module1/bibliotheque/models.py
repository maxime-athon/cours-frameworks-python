from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Auteur(db.Model):
    __tablename__ = 'auteurs'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    nationalite = db.Column(db.String(100))
    biographie = db.Column(db.Text)
    # Un auteur peut avoir plusieurs livres
    livres = db.relationship('Livre', backref='auteur', lazy='dynamic')

    def to_dict(self, with_livres=False):
        d = {'id': self.id, 'nom': self.nom, 'prenom': self.prenom,
             'nationalite': self.nationalite, 'nb_livres': self.livres.count()}
        if with_livres:
            d['livres'] = [l.to_dict() for l in self.livres.all()]
        return d


class Livre(db.Model):
    __tablename__ = 'livres'
    id = db.Column(db.Integer, primary_key=True)
    titre = db.Column(db.String(200), nullable=False)
    isbn = db.Column(db.String(20), unique=True, nullable=False)
    annee_publication = db.Column(db.Integer)
    genre = db.Column(db.String(50))
    nb_exemplaires = db.Column(db.Integer, default=1)
    description = db.Column(db.Text)
    auteur_id = db.Column(db.Integer, db.ForeignKey('auteurs.id'), nullable=False)
    emprunts = db.relationship('Emprunt', backref='livre', lazy='dynamic')

    @property
    def dispo(self):
        """Nb d'exemplaires disponibles = total-emprunts non rendus."""
        return self.nb_exemplaires - self.emprunts.filter_by(rendu=False).count()

    @property
    def est_disponible(self):
        return self.dispo > 0

    def to_dict(self):
        return {
            'id': self.id, 'titre': self.titre, 'isbn': self.isbn,
            'annee': self.annee_publication, 'genre': self.genre,
            'auteur': f'{self.auteur.prenom} {self.auteur.nom}',
            'auteur_id': self.auteur_id,
            'nb_exemplaires': self.nb_exemplaires,
            'disponibles': self.dispo,
            'disponible': self.est_disponible,
        }


class Emprunteur(db.Model):
    __tablename__ = 'emprunteurs'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telephone = db.Column(db.String(20))
    emprunts = db.relationship('Emprunt', backref='emprunteur', lazy='dynamic')

    @property
    def actifs(self):
        return self.emprunts.filter_by(rendu=False).count()

    def to_dict(self):
        return {'id': self.id, 'nom': self.nom, 'prenom': self.prenom,
                'email': self.email, 'telephone': self.telephone,
                'emprunts_actifs': self.actifs}


class Emprunt(db.Model):
    __tablename__ = 'emprunts'
    id = db.Column(db.Integer, primary_key=True)
    date_emprunt = db.Column(db.Date, default=date.today, nullable=False)
    date_retour_prevue = db.Column(db.Date, nullable=False)
    date_retour_effective = db.Column(db.Date, nullable=True)
    rendu = db.Column(db.Boolean, default=False)
    livre_id = db.Column(db.Integer, db.ForeignKey('livres.id'), nullable=False)
    emprunteur_id = db.Column(db.Integer, db.ForeignKey('emprunteurs.id'), nullable=False)

    @property
    def est_en_retard(self):
        """Vrai si non rendu et date de retour prevue depassee."""
        return not self.rendu and date.today() > self.date_retour_prevue

    def to_dict(self):
        return {
            'id': self.id,
            'livre': self.livre.titre,
            'emprunteur': f'{self.emprunteur.prenom} {self.emprunteur.nom}',
            'date_emprunt': self.date_emprunt.isoformat(),
            'date_retour_prevue': self.date_retour_prevue.isoformat(),
            'date_retour_effective': self.date_retour_effective.isoformat()
            if self.date_retour_effective else None,
            'rendu': self.rendu,
            'en_retard': self.est_en_retard,
        }