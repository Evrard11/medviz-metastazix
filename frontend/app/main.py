from dash import Dash, html

app = Dash()

app.layout = [html.Div(children='Hello World')]

app.run(host="0.0.0.0", port=80, debug=True)
