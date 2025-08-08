from flask import Flask
from modules.document import routes

app = Flask(__name__)

routes.register_document_routes(app)


@app.route("/")
def hello_world():
    return "Hello, World!"


if __name__ == "__main__":
    app.run(debug=True)
