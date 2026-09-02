"""Import-safe app context for the RQ worker / scheduler processes."""

import os

from .app import create_app


def bootstrap_app_context():
    """Return a Flask app context bound to the worker process.

    Reuses the same env-driven configuration as the WebApi process. Workers
    never bind a port; they only need Mongo + Redis connections to run jobs.
    """
    app = create_app()
    return app.app_context()