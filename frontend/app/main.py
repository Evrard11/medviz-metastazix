from core import app
from layouts.main_layout import layout
from callbacks.interactions import register_callbacks

app.layout = layout

register_callbacks()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050, debug=True)
