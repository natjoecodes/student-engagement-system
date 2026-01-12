from flask import Flask, jsonify
from flask_cors import CORS
from attention_engine import AttentionEngine

app = Flask(__name__)
CORS(app)

engine = AttentionEngine()

@app.route("/attention")
def attention():
    value = engine.get_attention()
    return jsonify({"attention": value})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)