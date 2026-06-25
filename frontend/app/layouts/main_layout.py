import dash_mantine_components as dmc
from dash_iconify import DashIconify
from data.db_client import get_patients
from components.cards import patient_card, anomaly_card
from dash import dcc, html
import plotly.express as px
import numpy as np
import dash_vtk
from data.backend_integration import segmenter, lung_points, lung_polys

# Mock 2D image
mock_image = np.zeros((512, 512))
fig_2d = px.imshow(mock_image, color_continuous_scale='gray', template="plotly_dark")
fig_2d.update_layout(
    dragmode="drawclosedpath",
    newshape=dict(line_color="dodgerblue", opacity=0.8, line_width=2),
    margin=dict(l=0, r=0, b=0, t=0),
    coloraxis_showscale=False,
    uirevision='constant'
)
fig_2d.update_xaxes(showticklabels=False, showgrid=False, zeroline=False, visible=False)
fig_2d.update_yaxes(showticklabels=False, showgrid=False, zeroline=False, visible=False)

patient_modal = dmc.Modal(
    title="Nouveau Patient",
    id="patient-modal",
    zIndex=10000,
    children=[
        dmc.TextInput(label="Nom Complet", id="patient-name-input", placeholder="Ex: Jean Dupont"),
        dmc.NumberInput(label="Âge", id="patient-age-input", value=45, min=0, max=120),
        dmc.Select(
            label="Sexe",
            id="patient-sex-input",
            data=[
                {"value": "M", "label": "Homme"},
                {"value": "F", "label": "Femme"},
                {"value": "O", "label": "Autre"}
            ],
            value="M",
            comboboxProps={"zIndex": 10005},
            style={"position": "relative", "zIndex": 10005}
        ),
        dmc.Button("Créer le patient et Analyser", id="submit-patient-btn", fullWidth=True, mt="md", color="cyan")
    ]
)

report_modal = dmc.Modal(
    title="Rapport Médical",
    id="report-modal",
    size="lg",
    zIndex=10000,
    children=[
        html.Div(id="report-content", style={"padding": "10px"}),
        dmc.Group(
            justify="flex-end",
            mt="xl",
            children=[
                dmc.Button("Fermer", id="close-report-btn", variant="default"),
                dmc.Button("Imprimer (PDF)", id="print-report-btn", color="cyan", leftSection=DashIconify(icon="radix-icons:printer"))
            ]
        )
    ]
)

left_column = dmc.Stack(
    w=320,
    h="100vh",
    p="md",
    style={"borderRight": "1px solid var(--mantine-color-default-border)", "backgroundColor": "var(--mantine-color-body)"},
    children=[
        patient_modal,
        report_modal,
        dmc.Title("Radiologie 3D", order=2, c="cyan", mb="sm"),
        dmc.TextInput(
            placeholder="Rechercher un patient...",
            leftSection=DashIconify(icon="radix-icons:magnifying-glass"),
            radius="md",
            mb="xs"
        ),
        dcc.Upload(
            id='upload-dicom',
            children=dmc.Button(
                "Importer DICOM (ZIP)",
                fullWidth=True,
                leftSection=DashIconify(icon="radix-icons:upload"),
                color="cyan",
                variant="outline",
                mb="md"
            ),
            multiple=False
        ),
        dmc.ScrollArea(
            offsetScrollbars=True,
            flex=1,
            children=dmc.Stack(gap="xs", id="patients-list", children=[])
        )
    ]
)

center_column = dmc.Stack(
    flex=1,
    h="100vh",
    p="md",
    gap="md",
    children=[
        dcc.Store(id='patients-store', data=[]),
        dcc.Store(id='annotations-store', data=[]),
        dcc.Store(id='selected-anomaly-store', data=None),
        dcc.Store(id='current-3d-model', data=None),
        dcc.Store(id='upload-content-store', data=None),
        dcc.Store(id='ann-count-store', data=0),
        dcc.Loading(
            id="loading-3d",
            type="circle",
            color="cyan",
            parent_style={"flex": 1, "display": "flex", "flexDirection": "column", "minHeight": 0},
            style={"flex": 1, "display": "flex", "flexDirection": "column", "minHeight": 0},
            children=[
                dmc.Group(
                    flex=1,
                    align="stretch",
                    gap="md",
                    wrap="nowrap",
                    children=[
                #3D VTK Card
                dmc.Card(
                    withBorder=True, radius="lg", flex=1,
                    style={"backgroundColor": "#000", "position": "relative", "display": "flex", "flexDirection": "column", "padding": 0},
                    children=[
                        # 3D Header
                        dmc.Group(
                            justify="space-between",
                            style={"backgroundColor": "rgba(20,20,20,0.8)", "padding": "8px 15px", "borderBottom": "1px solid var(--mantine-color-default-border)", "zIndex": 10},
                            children=[
                                dmc.Stack(gap=2, children=[
                                    dmc.Text("Modèle 3D interactif", fw=700, c="cyan", size="sm"),
                                    dmc.Text("Tourner le modèle avec la souris", c="dimmed", size="xs")
                                ]),
                                dmc.Popover(
                                    width=300,
                                    position="bottom-end",
                                    withArrow=True,
                                    shadow="md",
                                    children=[
                                        dmc.PopoverTarget(
                                            dmc.ActionIcon(
                                                DashIconify(icon="radix-icons:question-mark-circled", width=20),
                                                size="lg", variant="subtle", color="cyan"
                                            )
                                        ),
                                        dmc.PopoverDropdown(
                                            dmc.Stack(gap="xs", children=[
                                                dmc.Text("Paramètres d'affichage", fw=700, size="sm"),
                                                dmc.Text([html.B("Use shadow : "), "Active l'ombrage pour mieux percevoir la profondeur et les textures du volume."]),
                                                dmc.Text([html.B("Color map : "), "Change la palette de couleurs pour différencier les densités."]),
                                                dmc.Text([html.B("Graphique de couleur : "), "Permet de régler l'opacité. Modifiez la courbe pour rendre transparentes certaines parties (ex: tissus mous)."])
                                            ])
                                        )
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            id="vtk-container",
                            style={"width": "100%", "height": "100%", "flex": 1, "display": "flex", "position": "relative"},
                            children=[
                                dash_vtk.View(
                                    id="vtk-view",
                                    background=[0, 0, 0],
                                    style={"width": "100%", "height": "100%", "flex": 1},
                                    children=[
                                        dash_vtk.GeometryRepresentation(
                                            id="lung-mesh-repr",
                                            property={"color": [1, 1, 1], "opacity": 0.15, "edgeVisibility": False},
                                            children=[
                                                dash_vtk.PolyData(points=lung_points, polys=lung_polys)
                                            ]
                                        ),
                                        dash_vtk.GeometryRepresentation(id="slice-plane-repr"),
                                        html.Div(id="vtk-annotations-container", style={"display": "none"}, children=[])
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                #2D DICOM Card
                dmc.Card(
                    withBorder=True, radius="lg", flex=1, p=0,
                    style={"backgroundColor": "#000", "position": "relative", "display": "flex", "flexDirection": "column", "overflow": "hidden"},
                    children=[
                        # 2D Header
                        dmc.Group(
                            style={"backgroundColor": "rgba(20,20,20,0.8)", "padding": "8px 15px", "borderBottom": "1px solid var(--mantine-color-default-border)", "zIndex": 10},
                            children=[
                                dmc.Stack(gap=2, children=[
                                    dmc.Text("Scan 2D", fw=700, c="cyan", size="sm"),
                                    dmc.Text("Tracé manuel activé", c="dimmed", size="xs")
                                ])
                            ]
                        ),
                        html.Div(
                            id="2d-empty-state",
                            style={"width": "100%", "height": "100%", "display": "flex", "padding": "20px", "flex": 1},
                            children=[
                                dcc.Upload(
                                    id='upload-dicom-2d',
                                    children=dmc.Stack(
                                        align="center", justify="center", h="100%", w="100%", gap="xs",
                                        children=[
                                            DashIconify(icon="radix-icons:upload", width=64, color="var(--mantine-color-cyan-6)"),
                                            dmc.Text("Glissez et déposez un fichier DICOM (ZIP) ici", fw=500, size="lg"),
                                            dmc.Text("ou cliquez pour importer", size="sm", c="dimmed")
                                        ]
                                    ),
                                    style={
                                        'width': '100%', 'height': '100%', 'borderWidth': '2px', 'flex': 1,
                                        'borderStyle': 'dashed', 'borderColor': 'var(--mantine-color-cyan-8)',
                                        'borderRadius': '12px', 'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center',
                                        'cursor': 'pointer', 'backgroundColor': 'rgba(0, 255, 255, 0.05)'
                                    },
                                    multiple=False
                                )
                            ]
                        ),
                        html.Div(
                            id="2d-viewer-container",
                            style={"width": "100%", "height": "100%", "display": "none", "flex": 1, "flexDirection": "column"},
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
                                )
                            ]
                        )
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
                                dmc.Slider(id='slice-slider', min=1, max=segmenter.lung.shape[0], step=1, value=15, color="cyan", marks=None)
                            ]
                        ),
                        dmc.Text(f"Slice 15/{segmenter.lung.shape[0]}", id='slice-display', fw=700, c="cyan", w=100, ta="right")
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
        dmc.TextInput(id="anomaly-search-input", placeholder="Rechercher par nom ou slice...", leftSection=DashIconify(icon="radix-icons:magnifying-glass"), mb="sm"),
        dmc.Text("Anomalies Détectées", id="anomalies-title", fw=700, mt="sm", mb="xs"),
        dmc.ScrollArea(
            flex=1,
            type="auto",
            children=[
                dmc.Stack(gap="xs", id="anomalies-list", children=[])
            ]
        ),
        dmc.Text("Tracés manuels", id="traces-title", fw=700, mt="sm", mb="xs"),
        dmc.ScrollArea(
            flex=1,
            type="auto",
            children=[
                dmc.Box(
                    id="traces-container",
                    p="xs",
                    style={"border": "1px dashed var(--mantine-color-default-border)", "borderRadius": "8px", "textAlign": "center", "backgroundColor": "rgba(255,255,255,0.02)", "minHeight": "100px"},
                    children=dmc.Text("Aucun tracé en cours", c="dimmed", size="sm", mt="sm")
                )
            ]
        ),
        dmc.Button("Rapport Médical", id="open-report-btn", color="cyan", size="lg", radius="md", fullWidth=True, variant="filled")
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
