import dash
from dash import html
import dash_vtk

app = dash.Dash(__name__)
app.layout = html.Div([
    dash_vtk.View([
        dash_vtk.GeometryRepresentation(
            children=[
                dash_vtk.Algorithm(
                    vtkClass="vtkConeSource",
                    state={"resolution": 64}
                )
            ]
        ),
        html.Div(id="my-div", children=[
            dash_vtk.GeometryRepresentation(
                children=[
                    dash_vtk.Algorithm(
                        vtkClass="vtkCylinderSource",
                        state={"resolution": 64}
                    )
                ]
            )
        ])
    ])
])

if __name__ == '__main__':
    print("SUCCESS")
