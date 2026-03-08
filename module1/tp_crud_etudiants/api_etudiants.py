from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from marshmallow import Schema, fields, validates, ValidationError
from datetime import datetime
from sqlalchemy import or_





def create_app(config_name="default"):
    """
    Factory qui crée et configure l'application Flask.
    Utilisée par pytest pour lancer l'app en mode 'testing'.
    """
    app = Flask(__name__)

    if config_name == "testing":
        app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY="secret-test"
        )
    else:
        app.config.update(
            SQLALCHEMY_DATABASE_URI="sqlite:///etudiants.db",
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SECRET_KEY="secret-key"
        )

    # Initialiser la base
    db.init_app(app)

    # Enregistrer les routes déjà définies dans ce fichier
    with app.app_context():
        db.create_all()

    return app





app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///etudiants.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Etudiant(db.Model):
     __tablename__ = 'etudiants'
     id = db.Column(db.Integer, primary_key=True)
     matricule = db.Column(db.String(20), unique=True, nullable=False)
     nom = db.Column(db.String(100), nullable=False)
     prenom = db.Column(db.String(100), nullable=False)
     email = db.Column(db.String(150), unique=True, nullable=False)
     filiere = db.Column(db.String(100), nullable=False)
     annee = db.Column(db.Integer, nullable=False)
     date_insc = db.Column(db.DateTime, default=datetime.utcnow)
     notes = db.relationship('Note', backref='etudiant', lazy='dynamic', cascade='all, delete-orphan')

     @property
     def moyenne(self):
          all_notes = self.notes.all()
          if not all_notes:
               return None
          total = sum(n.valeur * n.coefficient for n in all_notes)
          coeff = sum(n.coefficient for n in all_notes)
          return round(total / coeff, 2) if coeff else 0

     def to_dict(self, with_notes=False):
          d = {
               'id': self.id,
               'matricule': self.matricule,
               'nom': self.nom,
               'prenom': self.prenom,
               'email': self.email,
               'filiere': self.filiere,
               'annee': self.annee,
               'moyenne': self.moyenne,
               'date_inscription': self.date_insc.isoformat() if self.date_insc else None,
          }
          if with_notes:
               d['notes'] = [n.to_dict() for n in self.notes.all()]
          return d


class Note(db.Model):
     __tablename__ = 'notes'
     id = db.Column(db.Integer, primary_key=True)
     matiere = db.Column(db.String(100), nullable=False)
     valeur = db.Column(db.Float, nullable=False)
     coefficient = db.Column(db.Float, default=1.0)
     date_examen = db.Column(db.Date, nullable=False)
     etudiant_id = db.Column(db.Integer, db.ForeignKey('etudiants.id'), nullable=False)

     def to_dict(self):
          return {
               'id': self.id,
               'matiere': self.matiere,
               'valeur': self.valeur,
               'coefficient': self.coefficient,
               'date_examen': self.date_examen.isoformat() if self.date_examen else None,
          }


# ---- Schemas ----
class EtudiantSchema(Schema):
     id = fields.Int(dump_only=True)
     matricule = fields.Str(required=True)
     nom = fields.Str(required=True)
     prenom = fields.Str(required=True)
     email = fields.Email(required=True)
     filiere = fields.Str(required=True)
     annee = fields.Int(required=True)

     # @validates('annee')
     # def valider_annee(self, v):
     #      if not (1 <= v <= 5):
     #           raise ValidationError('Annee entre 1 et 5.')


class NoteSchema(Schema):
     id = fields.Int(dump_only=True)
     matiere = fields.Str(required=True)
     valeur = fields.Float(required=True)
     coefficient = fields.Float(load_default=1.0)
     date_examen = fields.Date(required=True)
     etudiant_id = fields.Int(dump_only=True)

     # @validates('valeur')
     # def valider_note(self, v):
     #      if not (0 <= v <= 20):
     #           raise ValidationError('Note entre 0 et 20.')


etudiant_schema = EtudiantSchema()
etudiants_schema = EtudiantSchema(many=True)
note_schema = NoteSchema()


# ---- Utilitaire erreur ----
def erreur(msg, code, details=None):
     d = {'error': msg, 'code': code}
     if details:
          d['details'] = details
     return jsonify(d), code


@app.errorhandler(404)
def not_found(e):
     return erreur('Ressource introuvable', 404)


@app.errorhandler(500)
def server_err(e):
     db.session.rollback()
     return erreur('Erreur interne', 500)


# GET /api/etudiants  - liste avec filtres et pagination
@app.route('/api/etudiants', methods=['GET'])
def lister_etudiants():
     """Filtres : ?filiere=Maths&annee=2&q=Koffi&page=1&per_page=10"""
     filiere = request.args.get('filiere')
     annee = request.args.get('annee', type=int)
     recherche = request.args.get('q')
     page = request.args.get('page', 1, type=int)
     per_page = request.args.get('per_page', 10, type=int)

     q = Etudiant.query
     if filiere:
          q = q.filter(Etudiant.filiere.ilike(f'%{filiere}%'))
     if annee:
          q = q.filter_by(annee=annee)
     if recherche:
          t = f'%{recherche}%'
          q = q.filter(or_(Etudiant.nom.ilike(t), Etudiant.prenom.ilike(t), Etudiant.matricule.ilike(t)))

     pag = q.order_by(Etudiant.nom).paginate(page=page, per_page=per_page, error_out=False)
     return jsonify({
          'etudiants': [e.to_dict() for e in pag.items],
          'total': pag.total,
          'pages': pag.pages,
          'page': page,
     }), 200


# GET /api/etudiants/<id> - détail
@app.route('/api/etudiants/<int:eid>', methods=['GET'])
def get_etudiant(eid):
     e = Etudiant.query.get_or_404(eid)
     return jsonify(e.to_dict(with_notes=True)), 200


# POST /api/etudiants - créer
@app.route('/api/etudiants', methods=['POST'])
def creer_etudiant():
     data = request.get_json()
     if not data:
          return erreur('Corps JSON requis', 400)
     try:
          valide = etudiant_schema.load(data)
     except ValidationError as e:
          return erreur('Donnees invalides', 422, e.messages)

     if Etudiant.query.filter_by(matricule=valide['matricule']).first():
          return erreur('Matricule deja utilise', 409)

     etudiant = Etudiant(**valide)
     db.session.add(etudiant)
     try:
          db.session.commit()
     except Exception:
          db.session.rollback()
          return erreur('Erreur base de donnees', 500)
     return jsonify(etudiant.to_dict()), 201


# PUT /api/etudiants/<id> - modifier
@app.route('/api/etudiants/<int:eid>', methods=['PUT'])
def modifier_etudiant(eid):
     etudiant = Etudiant.query.get_or_404(eid)
     data = request.get_json() or {}
     try:
          valide = etudiant_schema.load(data, partial=True)
     except ValidationError as e:
          return erreur('Donnees invalides', 422, e.messages)
     for cle, val in valide.items():
          setattr(etudiant, cle, val)
     db.session.commit()
     return jsonify(etudiant.to_dict()), 200


# DELETE /api/etudiants/<id> - supprimer
@app.route('/api/etudiants/<int:eid>', methods=['DELETE'])
def supprimer_etudiant(eid):
     etudiant = Etudiant.query.get_or_404(eid)
     nom = f"{etudiant.prenom} {etudiant.nom}"
     db.session.delete(etudiant)
     db.session.commit()
     return jsonify({'message': f'{nom} supprime.'}), 200


# GET / POST /api/etudiants/<id>/notes
@app.route('/api/etudiants/<int:eid>/notes', methods=['GET'])
def get_notes(eid):
     e = Etudiant.query.get_or_404(eid)
     return jsonify({
          'etudiant': f'{e.prenom} {e.nom}',
          'notes': [n.to_dict() for n in e.notes.all()],
          'moyenne': e.moyenne,
     }), 200


@app.route('/api/etudiants/<int:eid>/notes', methods=['POST'])
def ajouter_note(eid):
     Etudiant.query.get_or_404(eid)  # 404 si absent
     data = request.get_json()
     if not data:
          return erreur('Corps JSON requis', 400)
     try:
          valide = note_schema.load(data)
     except ValidationError as err:
          return erreur('Donnees invalides', 422, err.messages)
     note = Note(**valide, etudiant_id=eid)
     db.session.add(note)
     db.session.commit()
     return jsonify(note.to_dict()), 201


with app.app_context():
     # Cree les tables si elles n'existent pas
     db.create_all()


if __name__ == '__main__':
     app.run(debug=True)