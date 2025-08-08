from flask import Blueprint
from controller import translate_controller

translate_bp = Blueprint('translate', __name__)

translate_bp.route('/translate', methods=['POST'])(translate_controller)
