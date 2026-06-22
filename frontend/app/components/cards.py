import dash_mantine_components as dmc
from dash import html
from dash_iconify import DashIconify

def patient_card(patient):
    """
    Generate a UI card displaying basic patient information.
    """
    initial = patient["name"][0]
    return html.Div(
        id={'type': 'patient-card', 'index': patient['id']},
        n_clicks=0,
        children=[
            dmc.Card(
                withBorder=True,
                shadow="sm",
                radius="md",
                p="sm",
                style={"cursor": "pointer"},
                children=[
                    dmc.Group(
                        wrap="nowrap",
                        children=[
                            dmc.Avatar(initial, size="md", color="cyan", radius="xl"),
                            dmc.Stack(
                                gap=2,
                                children=[
                                    dmc.Text(patient["name"], fw=700, size="sm"),
                                    dmc.Text(f"ID: {patient['id']} • {patient['age']} • {patient['date']}", size="xs", c="dimmed")
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
    )

def anomaly_card(anomaly):
    """
    Generate an interactive UI card displaying details of a specific anomaly, 
    including its location, size, and associated slice.
    """
    a_id = anomaly.get('id', 'unknown')
    
    return html.Div(
        id={'type': 'anomaly-card', 'index': a_id},
        n_clicks=0,
        children=[
            dmc.Card(
                withBorder=True,
                shadow="sm",
                radius="md",
                p="sm",
                style={"borderLeft": "4px solid var(--mantine-color-red-6)", "cursor": "pointer"},
                children=[
                    dmc.Group(
                        justify="space-between",
                        mb="xs",
                        children=[
                            dmc.Badge(a_id, color="red", variant="light", size="sm"),
                            dmc.Group(
                                gap="xs",
                                children=[
                                    dmc.Text(f"Slice {anomaly.get('slice', 'N/A')}", size="sm", c="cyan", fw=500),
                                    dmc.ActionIcon(
                                        DashIconify(icon="radix-icons:trash"),
                                        size="sm", color="red", variant="subtle",
                                        id={'type': 'delete-anomaly', 'index': a_id}
                                    )
                                ]
                            )
                        ]
                    ),
                    dmc.Text(f"Origine: {'Détection Automatique (IA)' if anomaly.get('loc') == 'Backend' else anomaly.get('loc', 'Tracés manuels')}", size="sm"),
                    dmc.Text(f"Taille: {anomaly.get('size', 'N/A')}", size="sm"),
                    dmc.Text(f"{anomaly.get('note', '')}", size="xs", c="dimmed", fs="italic", mt="xs")
                ]
            )
        ]
    )
