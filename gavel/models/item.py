from gavel.models import db
from gavel.models.tag import item_tag_table
import gavel.crowd_bt as crowd_bt
from sqlalchemy.orm.exc import NoResultFound

view_table = db.Table('view',
    db.Column('item_id', db.Integer, db.ForeignKey('item.id')),
    db.Column('annotator_id', db.Integer, db.ForeignKey('annotator.id'))
)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    uuid = db.Column(db.Text, nullable=True, unique=True)
    name = db.Column(db.Text, nullable=False)
    zone = db.Column(db.Text, nullable=False)
    location = db.Column(db.Text, nullable=False)
    tags = db.relationship('Tag', secondary=item_tag_table)
    link = db.Column(db.Text,nullable=False)
    description = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    viewed = db.relationship('Annotator', secondary=view_table,back_populates='viewed')
    prioritized = db.Column(db.Boolean, default=False, nullable=False)
    
    finalist = db.Column(db.Boolean, default=False, nullable=False)

    mu = db.Column(db.Float)
    sigma_sq = db.Column(db.Float)

    def __init__(self, uuid, name, zone, location, _tags_ignore_, link, description):
        self.name = name
        self.uuid = None if uuid=="" else uuid
        self.zone = zone
        self.location = location
        # Tags should be filled from somewhere else
        self.link = link
        self.description = description
        self.mu = crowd_bt.MU_PRIOR
        self.sigma_sq = crowd_bt.SIGMA_SQ_PRIOR

    @classmethod
    def by_id(cls, uid):
        if uid is None:
            return None
        try:
            item = cls.query.get(uid)
        except NoResultFound:
            item = None
        return item
