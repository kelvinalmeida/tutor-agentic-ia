import json
from . import db

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  # armazenar JSON string
    correct = db.Column(db.String(10), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'options': json.loads(self.options),  # retorna como lista
            'correct': self.correct,
            'domain_id': self.domain_id
        }


class VideoUpload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(255), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'path': self.path,
            'domain_id': self.domain_id
        }

class VideoYoutube(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(500), nullable=False)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'domain_id': self.domain_id
        }

class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

    pdfs = db.relationship('PDF', backref='domain', lazy='joined')
    exercises = db.relationship('Exercise', backref='domain', lazy='joined')
    videos_uploaded = db.relationship('VideoUpload', backref='domain', lazy='joined')
    videos_youtube = db.relationship('VideoYoutube', backref='domain', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'pdfs': [pdf.to_dict() for pdf in self.pdfs],
            'exercises': [ex.to_dict() for ex in self.exercises],
            'videos_uploaded': [v.to_dict() for v in self.videos_uploaded],
            'videos_youtube': [v.to_dict() for v in self.videos_youtube],
        }


class PDF(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # nome do arquivo
    path = db.Column(db.String(255), nullable=False)       # caminho do arquivo salvo
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'path': self.path,
            'domain_id': self.domain_id
        }
