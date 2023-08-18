#!/usr/bin/env python3
from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_flatpages import FlatPages
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_smorest import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_mptt import mptt_sessionmaker

from .parser import FlaskParser
from .reader.s3 import S3Reader
from .reader.test import TestReader
from .utils import datetimeformat, file_type
from .dummy_db import _populate_db


# subclass the db manager and insert the wrapper at session creation
class MPTTSQLAlchemy(SQLAlchemy):
    """A custom SQLAlchemy manager, to have control on session creation"""

    def create_session(self, options):
        """Override the original session factory creation"""
        Session = super().create_session(options)
        # Use wrapper from sqlalchemy_mptt that manage tree tables
        return mptt_sessionmaker(Session)


app = Flask(__name__, instance_relative_config=False)
db = MPTTSQLAlchemy()
parser = FlaskParser()
migrate = Migrate()
bootstrap = Bootstrap5()
restapi = Api()
pages = FlatPages()
ma = Marshmallow()


def register_api_blueprints(restapi):
    from .api.v1 import (
        cell,
        compound,
        identity,
        items,
        modality,
        plate,
        section,
        stack,
        tag,
    )

    restapi.register_blueprint(modality.blp)
    restapi.register_blueprint(compound.blp)
    restapi.register_blueprint(stack.blp)
    restapi.register_blueprint(plate.blp)
    restapi.register_blueprint(tag.blp)
    restapi.register_blueprint(section.blp)
    restapi.register_blueprint(items.blp)
    restapi.register_blueprint(cell.blp)
    restapi.register_blueprint(identity.blp)


def add_url_views(app):
    from .views.index import bp as main_bp

    app.register_blueprint(main_bp, url_prefix="/")

    from .models.cell import Cell, CellSchema
    from .models.compound import Compound, CompoundSchema
    from .models.item import Tag, TagSchema
    from .models.modality import Modality, ModalitySchema
    from .models.plate import Plate, PlateSchema
    from .models.section import Section, SectionSchema
    from .models.stack import Stack, StackSchema
    from .views import ItemView, ListView
    from .views.plate import PlateView
    from .views.stack import StackView

    # Add detail views
    for model, schema in zip(
        [
            Modality,
            Cell,
            Compound,
            Tag,
            Section,
        ],
        [
            ModalitySchema,
            CellSchema,
            CompoundSchema,
            TagSchema,
            SectionSchema,
        ],
    ):
        name = model.__name__.lower()
        app.add_url_rule(
            f"/{name}/detail/<uuid:id>",
            view_func=ItemView.as_view(
                f"{name}_detail", model, schema, app.config["ITEMS_PER_PAGE"]
            ),
        )

    app.add_url_rule(
        f"/plate/detail/<uuid:id>",
        view_func=PlateView.as_view(
            f"plate_detail", Plate, PlateSchema, app.config["ITEMS_PER_PAGE"]
        ),
    )
    app.add_url_rule(
        f"/stack/detail/<uuid:id>",
        view_func=StackView.as_view(
            f"stack_detail", Stack, StackSchema, app.config["ITEMS_PER_PAGE"]
        ),
    )
    app.add_url_rule(
        "/image/<uuid:id>",
        view_func=ItemView.as_view(f"image_detail"),
    )

    # Add list views
    for obj, schema in zip(
        [Modality, Cell, Compound, Plate, Stack, Tag],
        [
            ModalitySchema,
            CellSchema,
            CompoundSchema,
            PlateSchema,
            StackSchema,
            TagSchema,
        ],
    ):
        name = obj.__name__.lower()
        app.add_url_rule(
            f"/{name}/list/".lower(),
            view_func=ListView.as_view(
                f"{name}_list", obj, schema, app.config["ITEMS_PER_PAGE"]
            ),
        )


def create_app(mode):
    """
    Application factory
    """

    assert mode in ["test", "dev", "prod"]

    app = Flask(__name__, instance_relative_config=False)

    reader = S3Reader()
    if mode == "dev":
        app.config.from_object("app.config.dev")
    elif mode == "prod":
        app.config.from_object("app.config.prod")
    else:
        app.config.from_object("app.config.test")
        reader = TestReader()

    # set jinja filters
    app.jinja_env.filters["datetimeformat"] = datetimeformat
    app.jinja_env.filters["file_type"] = file_type
    app.jinja_env.filters["zip"] = zip

    restapi.init_app(app)
    register_api_blueprints(restapi)

    db.init_app(app)
    bootstrap.init_app(app)
    migrate.init_app(app, db)
    pages.init_app(app)
    parser.init_app(app, reader)
    ma.init_app(app)

    add_url_views(app)

    if mode == "test":
        with app.app_context():
            db.drop_all()
            db.create_all()
            _populate_db()

    return app
