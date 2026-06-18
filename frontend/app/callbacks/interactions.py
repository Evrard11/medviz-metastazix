from dash import Input, Output
from core import app

def register_callbacks():
    @app.callback(
        Output('slice-display', 'children'),
        Input('slice-slider', 'value')
    )
    def update_slice_display(value):
        return f"Slice {value}/45"
