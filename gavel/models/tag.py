from gavel.models import db
import gavel.crowd_bt as crowd_bt
from sqlalchemy.orm.exc import NoResultFound

item_tag_table = db.Table('item_tag',
    db.Column('item_id', db.Integer, db.ForeignKey('item.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    value = db.Column('value', db.Text, nullable=False, unique=True)
    items = db.relationship('Item', secondary=item_tag_table)

    def __init__(self, value):
        self.value = value
        

    @classmethod
    def by_value(cls, val):
        if val is None:
            return None
        try:
            tag = cls.query.filter(cls.value==val).one()
        except NoResultFound:
            tag = None
        return tag