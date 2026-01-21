from flask import Blueprint
from helpers import render_page, login_required

despachos_bp = Blueprint('despachos', __name__)

@despachos_bp.route('/despacho')
@login_required
def despacho_form():
    return render_page('despacho.html')

# Aquí agregaremos las APIs de guardar despacho más adelante