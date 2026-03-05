from flask import Blueprint, request, jsonify
from datetime import date, timedelta
from sqlalchemy import func
from models import db, Livre, Auteur, Emprunteur, Emprunt

bp = Blueprint('biblio', __name__, url_prefix='/api')





@bp.route('/auteurs', methods=['POST'])
def  ajouter_auteur():
    """Ajouter un nouveau auteur """
    data = request.get_json()

    # Vérifier que les données reçues son bonne
    if not isinstance(data, dict):
        return jsonify({'error': 'Données invalides, un objet JSON est attendu.'}), 400
    
    # 2. Vérifier la présence des champs obligatoires
    required_fields = ['nom', 'prenom']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Données manquantes, "nom" et "prenom" sont requis.'}), 400

    # 3. Vérifier si l'auteur n'existe pas déjà
    if Auteur.query.filter_by(nom=data['nom'], prenom=data['prenom']).first():
        return jsonify({'error': 'Cet auteur existe déjà'}), 409

    auteur = Auteur(
        nom=data['nom'],
        prenom=data['prenom'],
        nationalite=data.get('nationalite', ''), # Utiliser .get() pour les champs optionnels
        biographie=data.get('biographie', ''),
    )
    db.session.add(auteur)
    db.session.commit()
    # 4. Corriger la structure de la réponse JSON
    return jsonify({'message': 'Auteur ajouté avec succès !', 'auteur': auteur.to_dict()}), 201

@bp.route('/auteurs' , methods=['GET'])
def lister_auteurs():
    """Obtenir la liste des Auteurs"""
    auteurs = Auteur.query.all()
    return jsonify({'auteurs': [auteur.to_dict() for auteur in auteurs],
                    'total': len(auteurs)})

@bp.route('/livres', methods=['GET'])
def lister_livres():
    """
    GET /api/livres?genre=Roman&q=Hugo&disponible=true
    Filtres optionnels : genre, recherche textuelle (q), disponibilite.
    """
    genre = request.args.get('genre')
    q = request.args.get('q')
    dispo_str = request.args.get('disponible', 'false')
    query = Livre.query

    if genre:
        query = query.filter(Livre.genre.ilike(f'%{genre}%'))
    if q:
        # Recherche sur le titre OU le nom de l'auteur
        query = query.join(Auteur).filter(
            db.or_(Livre.titre.ilike(f'%{q}%'), Auteur.nom.ilike(f'%{q}%'))
        )

    if dispo_str == 'true':
        # Sous-requête pour compter les emprunts actifs par livre
        subquery = db.session.query(
            Emprunt.livre_id,
            func.count(Emprunt.id).label('emprunts_actifs')
        ).filter(Emprunt.rendu == False).group_by(Emprunt.livre_id).subquery()

        # Jointure externe et filtre
        query = query.outerjoin(subquery, Livre.id == subquery.c.livre_id).filter(
            Livre.nb_exemplaires > func.coalesce(subquery.c.emprunts_actifs, 0)
        )

    livres = query.all()

    return jsonify({'livres': [l.to_dict() for l in livres],
                    'total': len(livres)}), 200


@bp.route('/livres', methods=['POST'])
def ajouter_livre():
    """Ajouter un nouveau livre. L'auteur doit deja exister en base."""
    data = request.get_json()
    # Verifier que l'auteur existe (renvoie 404 sinon)
    Auteur.query.get_or_404(data.get('auteur_id', 0))
    # Verifier l'unicite de l'ISBN
    if Livre.query.filter_by(isbn=data['isbn']).first():
        return jsonify({'error': 'ISBN deja existant'}), 409

    livre = Livre(
        titre=data['titre'], isbn=data['isbn'],
        auteur_id=data['auteur_id'],
        annee_publication=data.get('annee_publication'),
        genre=data.get('genre'), description=data.get('description'),
        nb_exemplaires=data.get('nb_exemplaires', 1)
    )
    db.session.add(livre)
    db.session.commit()
    return jsonify(livre.to_dict()), 201


@bp.route('/emprunteurs', methods=['GET'])
def lister_emprunteurs():
    """Lister tous les emprunteurs."""
    emprunteurs = Emprunteur.query.all()
    return jsonify({'emprunteurs': [e.to_dict() for e in emprunteurs],
                    'total': len(emprunteurs)}), 200


@bp.route('/emprunteurs', methods=['POST'])
def ajouter_emprunteur():
    """Ajouter un nouvel emprunteur."""
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({'error': 'Données invalides, un objet JSON est attendu.'}), 400

    required_fields = ['nom', 'prenom', 'email']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Données manquantes, "nom", "prenom" et "email" sont requis.'}), 400

    if Emprunteur.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Cet email est déjà utilisé'}), 409

    emprunteur = Emprunteur(
        nom=data['nom'],
        prenom=data['prenom'],
        email=data['email'],
        telephone=data.get('telephone')
    )
    db.session.add(emprunteur)
    db.session.commit()
    return jsonify({'message': 'Emprunteur ajouté avec succès !', 'emprunteur': emprunteur.to_dict()}), 201


@bp.route('/emprunts', methods=['POST'])
def creer_emprunt():
    """
    Enregistrer un emprunt.
    Verifie : disponibilite du livre + emprunt deja en cours pour ce lecteur.
    """
    data = request.get_json()
    livre = Livre.query.get_or_404(data.get('livre_id', 0))
    emprunteur = Emprunteur.query.get_or_404(data.get('emprunteur_id', 0))
    

    # Verfier la disponibilite
    if not livre.est_disponible:
        return jsonify({'error': f'"{livre.titre}" non disponible',
                        'dispo': 0}), 409

    # Eviter le doublon : meme livre, meme emprunteur, non rendu
    if Emprunt.query.filter_by(livre_id=livre.id,
                               emprunteur_id=emprunteur.id,
                               rendu=False).first():
        return jsonify({'error': 'Cet emprunteur a deja ce livre'}), 409

    duree = data.get('duree_jours', 14)  # Duree par defaut : 14 jours
    emprunt = Emprunt(
        livre_id=livre.id, emprunteur_id=emprunteur.id,
        date_emprunt=date.today(),
        date_retour_prevue=date.today() + timedelta(days=duree)
    )
    db.session.add(emprunt)
    db.session.commit()
    return jsonify({'message': 'Emprunt enregistre !',
                    'emprunt': emprunt.to_dict()}), 201


@bp.route('/emprunts/<int:eid>/retour', methods=['POST'])
def enregistrer_retour(eid):
    """
    Marquer un emprunt comme rendu.
    Si la date de retour est depassee, un message de retard est inclus.
    """
    emprunt = Emprunt.query.get_or_404(eid)
    if emprunt.rendu:
        return jsonify({'error': 'Deja rendu'}), 400

    emprunt.rendu = True
    emprunt.date_retour_effective = date.today()
    db.session.commit()

    msg = 'Retour enregistre.'
    if emprunt.est_en_retard:
        retard = (date.today() - emprunt.date_retour_prevue).days
        msg += f' (Retard de {retard} jour(s))'
    return jsonify({'message': msg, 'emprunt': emprunt.to_dict()}), 200


@bp.route('/emprunts/en-retard', methods=['GET'])
def emprunts_en_retard():
    """Lister tous les emprunts dont la date de retour est depassee."""
    # Requête optimisée pour filtrer directement dans la base de données
    retards = Emprunt.query.filter(
        Emprunt.rendu == False,
        Emprunt.date_retour_prevue < date.today()
    ).all()
    return jsonify({'en_retard': [e.to_dict() for e in retards],
                    'total': len(retards)}), 200


@bp.route('/stats', methods=['GET'])
def statistiques():
    """Tableau de bord rapide de la bibliotheque."""
    # Sous-requête pour compter les emprunts actifs par livre
    subquery = db.session.query(
        Emprunt.livre_id,
        func.count(Emprunt.id).label('emprunts_actifs')
    ).filter(Emprunt.rendu == False).group_by(Emprunt.livre_id).subquery()

    # Compter les livres disponibles de manière optimisée
    livres_dispos_count = db.session.query(func.count(Livre.id)).outerjoin(
        subquery, Livre.id == subquery.c.livre_id
    ).filter(
        Livre.nb_exemplaires > func.coalesce(subquery.c.emprunts_actifs, 0)
    ).scalar()

    return jsonify({
        'livres': Livre.query.count(),
        'auteurs': Auteur.query.count(),
        'emprunteurs': Emprunteur.query.count(),
        'emprunts_actifs': Emprunt.query.filter_by(rendu=False).count(),
        'en_retard': Emprunt.query.filter(
            Emprunt.rendu == False,
            Emprunt.date_retour_prevue < date.today()
        ).count(),
        'livres_dispos': livres_dispos_count,
    }), 200


@bp.route('/auteurs/<int:auteur_id>', methods=['GET'])
def get_auteur(auteur_id):
    """Récupérer un auteur par ID."""
    auteur = Auteur.query.get_or_404(auteur_id)
    return jsonify(auteur.to_dict(with_livres=True)), 200