import dash_mantine_components as dmc
from dash_iconify import DashIconify
from data.mock_data import mock_patients, mock_anomalies
from components.cards import patient_card, anomaly_card
from dash import dcc
import plotly.express as px
import numpy as np
import dash_vtk
from data.backend_integration import segmenter, lung_points, lung_polys

# Mock 2D image
mock_image = np.zeros((512, 512))
fig_2d = px.imshow(mock_image, color_continuous_scale='gray', template="plotly_dark")
fig_2d.update_layout(
    dragmode="drawclosedpath",
    newshape=dict(line_color="cyan", opacity=0.8, line_width=2),
    margin=dict(l=0, r=0, b=0, t=0),
    coloraxis_showscale=False,
    xaxis=dict(showticklabels=False),
    yaxis=dict(showticklabels=False)
)

patient_cards = []
for p in mock_patients:
    patient_cards.append(patient_card(p))

left_column = dmc.Stack(
    w=320,
    h="100vh",
    p="md",
    style={"borderRight": "1px solid var(--mantine-color-default-border)", "backgroundColor": "var(--mantine-color-body)"},
    children=[
        dmc.Title("Radiologie 3D", order=2, c="cyan", mb="sm"),
        dmc.TextInput(
            placeholder="Rechercher un patient...",
            leftSection=DashIconify(icon="radix-icons:magnifying-glass"),
            radius="md",
            mb="xs"
        ),
        dmc.ScrollArea(
            offsetScrollbars=True,
            flex=1,
            children=dmc.Stack(gap="xs", children=patient_cards)
        )
    ]
)

center_column = dmc.Stack(
    flex=1,
    h="100vh",
    p="md",
    gap="md",
    children=[
        dcc.Store(id='annotations-store', data=[]),
        dcc.Store(id='selected-anomaly-store', data=None),
        dmc.Group(
            flex=1,
            align="stretch",
            gap="md",
            wrap="nowrap",
            children=[
                #3D VTK Card
                dmc.Card(
                    withBorder=True, radius="lg", flex=1,
                    style={"backgroundColor": "#000", "position": "relative", "display": "flex", "alignItems": "center", "justifyContent": "center"},
                    children=[
                        dmc.Stack(
                            gap=2,
                            style={"position": "absolute", "top": 15, "left": 15, "backgroundColor": "rgba(20,20,20,0.8)", "padding": "8px 12px", "borderRadius": "8px", "backdropFilter": "blur(4px)", "border": "1px solid var(--mantine-color-default-border)"},
                            children=[
                                dmc.Text("Modèle 3D interactif", fw=700, c="cyan", size="sm"),
                                dmc.Text("Tourner avec la souris", c="dimmed", size="xs")
                            ]
                        ),
                        dash_vtk.View(
                            id="vtk-view",
                            children=[
                                dash_vtk.GeometryRepresentation(
                                    children=[
                                        dash_vtk.PolyData(points=lung_points, polys=lung_polys)
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                #2D DICOM Card
                dmc.Card(
                    withBorder=True, radius="lg", flex=1, p=0,
                    style={"backgroundColor": "#000", "position": "relative", "display": "flex", "overflow": "hidden"},
                    children=[
                        dcc.Graph(
                            id='2d-viewer-graph',
                            figure=fig_2d,
                            style={"width": "100%", "height": "100%", "flex": 1},
                            config={
                                "displayModeBar": True,
                                "modeBarButtonsToAdd": ["drawclosedpath", "drawcircle", "drawrect", "eraseshape"],
                                "displaylogo": False
                            }
                        ),
                        dmc.Stack(
                            gap=2,
                            style={"position": "absolute", "top": 15, "left": 15, "backgroundColor": "rgba(20,20,20,0.8)", "padding": "8px 12px", "borderRadius": "8px", "backdropFilter": "blur(4px)", "border": "1px solid var(--mantine-color-default-border)", "zIndex": 10},
                            children=[
                                dmc.Text("Scan 2D", fw=700, c="cyan", size="sm"),
                                dmc.Text("Tracé manuel activé", c="dimmed", size="xs")
                            ]
                        )
                    ]
                )
            ]
        ),
        dmc.Card(
            withBorder=True, radius="md", p="md",
            children=[
                dmc.Group(
                    wrap="nowrap", align="center", gap="md",
                    children=[
                        dmc.ActionIcon(DashIconify(icon="radix-icons:play"), size="lg", variant="default", radius="md"),
                        dmc.ActionIcon(DashIconify(icon="radix-icons:pause"), size="lg", variant="default", radius="md"),
                        dmc.Box(
                            flex=1, px="md",
                            children=[
                                dmc.Slider(id='slice-slider', min=1, max=45, step=1, value=15, color="cyan", marks=None)
                            ]
                        ),
                        #TODO : Hardcoded for now
                        dmc.Text("Slice 15/45", id='slice-display', fw=700, c="cyan", w=100, ta="right")
                    ]
                )
            ]
        )
    ]
)

right_column = dmc.Stack(
    w=350,
    h="100vh",
    p="md",
    style={"borderLeft": "1px solid var(--mantine-color-default-border)", "backgroundColor": "var(--mantine-color-body)"},
    children=[
        dmc.Title("Analyse Manuelle", order=2, mb="xs"),
        dmc.Text("Anomalies Détectées", id="anomalies-title", fw=700, mt="sm", mb="xs"),
        dmc.Stack(gap="xs", id="anomalies-list", children=[]),
        dmc.Text("Tracés et Mesures", id="traces-title", fw=700, mt="sm", mb="xs"),
        dmc.Box(
            p="xl",
            style={"border": "1px dashed var(--mantine-color-default-border)", "borderRadius": "8px", "textAlign": "center", "backgroundColor": "rgba(255,255,255,0.02)"},
            children=dmc.Text("Aucun tracé en cours", c="dimmed", size="sm")
        ),
        dmc.Box(flex=1),
        dmc.Button("Rapport Médical", color="cyan", size="lg", radius="md", fullWidth=True, variant="filled")
    ]
)

layout = dmc.MantineProvider(
    forceColorScheme="dark",
    theme={
        "primaryColor": "cyan",
        "fontFamily": "system-ui, -apple-system, sans-serif"
    },
    children=[
        dmc.Flex(
            h="100vh", w="100vw", m="-8px", wrap="nowrap", style={"overflow": "hidden"},
            children=[left_column, center_column, right_column]
        )
    ]
)
