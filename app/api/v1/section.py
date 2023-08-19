#!/usr/bin/env python3

from flask_smorest import Blueprint
from app.utils import record_exists
from flask.views import MethodView
from flask_smorest import abort

from ... import db
from ...models.cell import Cell
from ...models.compound import Compound
from ...models.plate import Plate
from ...models.section import Section, SectionSchema
from ...models.stack import Stack
from . import admin_required

blp = Blueprint(
    "Section",
    "Section",
    url_prefix="/api/v1",
    description="Spatially contiguous subset of wells in a plate",
)

def range_subset(range1, range2):
    """Whether range1 is a subset of range2."""
    if not range1:
        return True  # empty range is subset of anything
    if not range2:
        return False  # non-empty range can't be subset of empty range
    if len(range1) > 1 and range1.step % range2.step:
        return False  # must have a single value or integer multiple step
    return range1.start in range2 and range1[-1] in range2


def make_grid(row_start, row_end, col_start, col_end, *args, **kwargs):
    row_range = [i for i in range(ord(row_start), ord(row_end) + 1)]
    col_range = [i for i in range(col_start, col_end + 1)]
    coordinates = [(r, c) for r in row_range for c in col_range]
    return coordinates


@blp.route("/plate/<uuid:plate_id>/sections")
class SectionsAPI(MethodView):
    @blp.response(200, SectionSchema(many=True))
    def get(self, plate_id):
        """Get all sections from plate ID"""

        res = record_exists(db,Plate, plate_id)

        return res.first().sections

    @admin_required
    @blp.response(204)
    def delete(self, plate_id):
        """Delete all sections"""

        res = record_exists(db,Plate, plate_id)
        for s in res.first().sections:
            res = SectionAPI._delete(s.id)

    @admin_required
    @blp.arguments(SectionSchema)
    @blp.response(201, SectionSchema)
    def post(self, data, plate_id):
        """Add a new section"""

        data["plate_id"] = plate_id
        res = SectionAPI._create(data)

        return res


@blp.route("/section/<uuid:id>")
class SectionAPI(MethodView):
    @blp.response(200, SectionSchema)
    def get(self, id):
        """Get section"""

        res = record_exists(db,Section, id)

        return res.first()

    @admin_required
    @blp.arguments(SectionSchema)
    @blp.response(200, SectionSchema)
    def put(self, update_data, id):
        """Update section"""
        res = SectionAPI._update(id, update_data).first()

        return res

    @admin_required
    @blp.arguments(SectionSchema)
    @blp.response(200, SectionSchema)
    def patch(self, update_data, id):
        """Patch section"""
        res = SectionAPI._update(id, update_data).first()

        return res

    @admin_required
    @blp.response(204)
    def delete(self, id):
        """Delete section"""

        res = SectionAPI._delete(id)

    @staticmethod
    def _check_range(plate_id, a):
        """
        check that requested range contained in a matches available range of plate with ID timepoint_id

        a: dicts that contain keys row_start, row_end, col_start, col_end
        """

        # get row and col range of plate
        plate = db.session.query(Plate).filter_by(id=a["plate_id"]).first()
        items = plate.items
        rows = [im.row for im in items]
        cols = [im.col for im in items]
        row_range = range(ord(min(rows)), ord(max(rows)))
        col_range = range(min(cols), max(cols))

        # compare with requested range
        if not range_subset(
            range(ord(a["row_start"]), ord(a["row_end"])), row_range
        ) and range_subset(range(a["col_start"], a["col_end"]), col_range):
            abort(
                409,
                message="Requested section is out of bounds for plate with id {} within rows: {}, cols: {}.".format(
                    plate_id,
                    (chr(row_range.start), chr(row_range.stop)),
                    (col_range.start, col_range.stop),
                ),
            )

    @staticmethod
    def _check_overlap(a, b):
        """
        check if new section overlaps existing sections

        a, b: dicts that contain keys row_start, row_end, col_start, col_end
        """
        section_coords = make_grid(**a)
        new_section_coords = make_grid(**b)

        if set(section_coords) & set(new_section_coords):
            abort(409, message="Requested section overlaps with existing section.")

    @staticmethod
    def _create(data):

        record_exists(db,Cell, value=data["cell_id"], field="id")
        record_exists(db,Compound, value=data["compound_id"], field="id")
        record_exists(db,Stack, value=data["stack_id"], field="id")

        SectionAPI._check_range(data["plate_id"], data)

        # check for overlap with existing sections of same plate
        existing_sections = db.session.query(Plate).filter_by(id=data["plate_id"]).first().sections
        for s in existing_sections:
            SectionAPI._check_overlap(s.__dict__, data)

        section = Section(**data)
        db.session.add(section)
        db.session.commit()

        return section

    @staticmethod
    def _delete(id):

        res = record_exists(db,Section, id, field="id").first()

        db.session.delete(res)
        db.session.commit()

    @staticmethod
    def _update(id, data):
        if "cell_code" in data.keys():
            data["cell_id"] = (
                record_exists(db,Cell, value=data["cell_code"], field="code").first().id
            )
            data.pop("cell_code", None)
        if "compound_name" in data.keys():
            data["compound_id"] = (
                record_exists(db,Compound, value=data["compound_name"], field="name")
                .first()
                .id
            )
            data.pop("compound_name", None)
        if "stack_name" in data.keys():
            data["stack_id"] = (
                record_exists(db,Stack, value=data["stack_name"], field="name").first().id
            )
            data.pop("stack_name", None)

        elem = db.session.query(Section).filter_by(id=id)

        if data:
            elem.update(data)
            db.session.commit()
        return elem
