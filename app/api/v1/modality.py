#!/usr/bin/env python3

from app import models as mdl
from app.schemas.modality import ModalitySchema
from app.utils import record_exists
from flask.views import MethodView
from flask_smorest import Blueprint

from ... import db
from .utils import admin_required, check_dependencies, check_duplicate

blp = Blueprint(
    "Modality",
    "Modality",
    url_prefix="/api/v1/modalities",
    description="Item modality",
)


@blp.route("/<uuid:id>")
class Modality(MethodView):
    model = mdl.Modality

    @blp.response(200, ModalitySchema)
    def get(self, id):
        """Get modality"""

        return mdl.Modality.query.get_or_404(id)

    @admin_required
    @blp.arguments(ModalitySchema)
    @blp.response(200, ModalitySchema)
    def patch(self, update_data, id):
        """Update modality"""

        res = mdl.Modality.query.get_or_404(id)
        res.update(update_data)
        db.session.commit()

        return res

    @admin_required
    @blp.response(204)
    def delete(self, id):
        """Delete modality"""

        res = mdl.Modality.query.get_or_404(id)

        check_dependencies(mdl.Modality, value=id, field="id", remote="stacks")

        db.session.delete(res)
        db.session.commit()


@blp.route("/")
class Modalities(MethodView):
    @blp.response(200, ModalitySchema(many=True))
    def get(self):
        """Get all modalities"""
        item = mdl.Modality.query.all()
        return item

    @admin_required
    @blp.arguments(ModalitySchema)
    @blp.response(201, ModalitySchema)
    def post(self, data):
        """Add a new modality"""
        check_duplicate(db.session, mdl.Modality, name=data['name'])
        res = mdl.Modality(**data)
        db.session.add(res)
        db.session.commit()

        return res
