from flask import Flask
from routes import translate_bp

app = Flask(__name__)
app.register_blueprint(translate_bp)

print("Blueprint registered")

if __name__ == '__main__':
    app.run(debug=True)
