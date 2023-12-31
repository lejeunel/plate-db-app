import uuid

from app.extensions import db
from sqlalchemy_utils.types.uuid import UUIDType
from .mixins import UpdateMixin


class Stack(db.Model, UpdateMixin):
    """
    This allows to group different modalities
    """

    __tablename__ = "stack"

    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4, index=True)
    name = db.Column(db.String(100))
    comment = db.Column(db.Text())


    def __repr__(self):
        return f"<Stack{self.name}>"


class StackModalityAssociation(db.Model):
    """
    Association model between stack and modality.
    Allows to set regular expression to match file name
    """

    __tablename__ = "stack_modality_assoc"
    id = db.Column(UUIDType, primary_key=True, default=uuid.uuid4)
    stack_id = db.Column(db.ForeignKey("stack.id"), primary_key=True, index=True)
    modality_id = db.Column(db.ForeignKey("modality.id"), primary_key=True, index=True)
    chan = db.Column(db.Integer())
    regexp = db.Column(db.String(50))


