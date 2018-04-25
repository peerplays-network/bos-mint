from flask import Flask, redirect, url_for, session, current_app, request
from flaskext.markdown import Markdown
from . import app, assets, views, config, db, forms
from .utils import strfdelta
from .node import Node, ApiServerDown

# # Blueprints
# from .referral import referral
# from .wallet import wallet
# app.register_blueprint(referral, url_prefix="/referral")
# app.register_blueprint(wallet, url_prefix="/wallet")

# Config markdown
markdown = Markdown(
    app,
    extensions=['meta',
                'tables'
                ],
    safe_mode=True,
    output_format='html4',
)


@app.template_filter('datetime')
def _jinja2_filter_datetime(date, fmt=None):
    if not date:
        return "unkown"
    if fmt:
        return strfdelta(date, fmt)
    else:
        return strfdelta(date, '{days} days {hours} hours')
