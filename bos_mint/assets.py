import os
from flask_assets import Bundle, Environment
from . import app

# Assets
webassets = Environment(app)
webassets.load_path = [
    os.path.join(os.path.dirname(__file__), "static"),
    os.path.join(os.path.dirname(__file__), "bower_components")
]
webassets.manifest = 'cache' if not app.debug else False
webassets.cache = not app.debug
webassets.debug = True  # app.debug

js_main = Bundle(
    "js/src/main.js",
    output="js/main.js"
)

css_main = Bundle(
    "css/src/styles.css",
    output="css/main.css"
)

js_libs = Bundle(
    "jquery/dist/jquery.min.js",
    "semantic-ui/dist/semantic.min.js",
    output="js/libs.js"
)

css_libs = Bundle(
    "font-awesome/web-fonts-with-css/css/fontawesome.min.css",
    "semantic-ui/dist/semantic.min.css",
    output="css/libs.css"
)

webassets.register('js_main', js_main)
webassets.register('js_libs', js_libs)
webassets.register('css_main', css_main)
webassets.register('css_libs', css_libs)
