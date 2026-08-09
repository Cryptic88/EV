from flask import Flask, render_template, jsonify

from core.state import AssistantState


def create_app(state: AssistantState):

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/api/status")
    def status():

        return jsonify({
            "status": getattr(
                state,
                "current_status",
                "idle"
            )
        })

    @app.route("/api/stop", methods=["POST"])
    def stop():

        state.stop()

        return jsonify({
            "success": True
        })

    return app