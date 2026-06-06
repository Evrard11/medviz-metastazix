import dash_mantine_components as dmc

def patient_card(patient):
    initial = patient["name"][0]
    return dmc.Card(
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

def anomaly_card(anomaly):
    return dmc.Card(
        withBorder=True,
        shadow="sm",
        radius="md",
        p="sm",
        style={"borderLeft": "4px solid var(--mantine-color-red-6)"},
        children=[
            dmc.Group(
                justify="space-between",
                mb="xs",
                children=[
                    dmc.Badge(anomaly['id'], color="red", variant="light", size="sm"),
                    dmc.Text(f"Slice {anomaly['slice']}", size="sm", c="cyan", fw=500)
                ]
            ),
            dmc.Text(f"Localisation: {anomaly['loc']}", size="sm"),
            dmc.Text(f"Taille: {anomaly['size']}", size="sm"),
            dmc.Text(f"{anomaly['note']}", size="xs", c="dimmed", fs="italic", mt="xs")
        ]
    )
