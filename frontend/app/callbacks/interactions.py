from dash import Input, Output, State, ALL, ctx, no_update, Patch
from core import app
import dash_vtk
import plotly.express as px
import uuid
import math
from data.backend_integration import segmenter, lung_points, lung_polys
from components.cards import anomaly_card
from utils.parsing_utils import svg_path_to_vtk_polydata

# region HELPERS

import uuid as _uuid
import numpy as np

def _parse_anomalies(anomalies: list) -> list:
    """Convert backend anomaly dicts into annotation store entries (1 per nodule)."""
    annotations = []
    for res in anomalies:
        z1, y1, x1, z2, y2, x2 = res["bbox"]
        score = res.get("score", 0)
        pred = "Malignant" if score > 0.5 else "Benign"
        annotations.append({
            "id":         f"AUTO-{_uuid.uuid4().hex[:8].upper()}",
            "slice":      int((z1 + z2) / 2) + 1,   # central slice, 1-indexed
            "z_range":    [int(z1), int(z2)],         # full extent for 2-D filtering
            "type":       "circle",
            "x0": x1, "y0": y1, "x1": x2, "y1": y2,
            "loc":        "Backend",
            "size":       f"{abs((x2-x1)*(y2-y1)*(z2-z1))} vox",
            "note":       f"Score: {score:.2f} ({pred})",
            "prediction": 1 if score > 0.5 else 0,
        })
    return annotations


def _build_vtk_annotations_list(store_data, selected_anomaly, model_data):
    import dash_vtk
    import math
    reps = []
    spacing = model_data.get("spacing", [1, 1, 1]) if model_data else [1, 1, 1]
    
    for ann in (store_data or []):
        color = ([1, 1, 0] if selected_anomaly == ann.get('id')
                 else ([1, 0, 0] if ann.get('prediction') == 1 else [0, 1, 0])
        if 'prediction' in ann
        else ([1, 1, 0] if selected_anomaly == ann.get('id') else [0, 0, 1]))

        if ann.get('loc') == 'Backend' and 'z_range' in ann:
            z1, z2 = ann['z_range']
            cx = (ann['x0'] + ann['x1']) / 2 * spacing[0]
            cy = (ann['y0'] + ann['y1']) / 2 * spacing[1]
            cz = (z1 + z2) / 2 * spacing[2]
            r = max(
                abs(ann['x1'] - ann['x0']) / 2 * spacing[0],
                abs(ann['y1'] - ann['y0']) / 2 * spacing[1],
                abs(z2 - z1) / 2 * spacing[2],
            )
            reps.append(
                dash_vtk.GeometryRepresentation(
                    property={"color": color, "opacity": 0.35},
                    children=[dash_vtk.Algorithm(
                        vtkClass="vtkSphereSource",
                        state={"center": [cx, cy, cz], "radius": r,
                               "thetaResolution": 16, "phiResolution": 16}
                    )]
                )
            )
        else:
            path_str = None
            if ann.get('type') in ['path', 'line'] or 'path' in ann:
                path_str = ann.get('path')
            elif ann.get('type') == 'rect':
                x0, y0 = ann.get('x0', 0), ann.get('y0', 0)
                x1, y1 = ann.get('x1', 0), ann.get('y1', 0)
                path_str = f"M {x0},{y0} L {x1},{y0} L {x1},{y1} L {x0},{y1} Z"
            elif ann.get('type') == 'circle':
                x0, y0 = ann.get('x0', 0), ann.get('y0', 0)
                x1, y1 = ann.get('x1', 0), ann.get('y1', 0)
                cx_2d, cy_2d = (x0+x1)/2, (y0+y1)/2
                rx, ry = abs(x1-x0)/2, abs(y1-y0)/2
                pts = []
                for i in range(16):
                    ang = i * math.pi / 8
                    pts.append(f"{cx_2d + rx*math.cos(ang)},{cy_2d + ry*math.sin(ang)}")
                path_str = f"M {pts[0]} " + " ".join([f"L {p}" for p in pts[1:]]) + " Z"

            if path_str:
                pts, polys = svg_path_to_vtk_polydata(path_str, ann.get('slice', 1) - 1, spacing)
                reps.append(
                    dash_vtk.GeometryRepresentation(
                        property={"color": color, "lineSegment": True, "lineWidth": 3},
                        children=[dash_vtk.PolyData(points=pts, polys=polys)]
                    )
                )
    return reps


def _apply_resp_data(resp_data: dict) -> list:
    """
    Side-effect: update segmenter.lung from the volume in resp_data.
    Returns the annotation list.
    """
    if "volume" in resp_data:
        dims = resp_data["dimensions"]
        vol_array = np.array(resp_data["volume"], dtype=np.uint8).reshape(
            (dims[2], dims[1], dims[0])
        )
        segmenter.lung = vol_array

    return _parse_anomalies(resp_data.get("anomalies", []))

def _call_backend(patient_id: str) -> dict | None:
    import os, requests
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
    try:
        resp = requests.post(f"{BACKEND_URL}/process_dicom", json={"patient_id": patient_id})
        return resp.json()
    except Exception as e:
        print(f"Backend error: {e}")
        return None

# endregion HELPERS

def register_callbacks():
    """
    Register all Dash callbacks for interactivity, linking the UI components 
    to the backend logic and data store.
    """
    @app.callback(
        Output('annotations-store', 'data'),
        Input('2d-viewer-graph', 'relayoutData'),
        State('annotations-store', 'data'),
        State('slice-slider', 'value')
    )
    def capture_shapes(relayout_data, store_data, current_slice):
        """
        Capture manual drawing shapes from the 2D viewer and append them 
        to the annotations store data.
        """
        if not relayout_data or 'shapes' not in relayout_data:
            return no_update
        
        shapes = relayout_data['shapes']
        new_data = []
        for ann in store_data:
            if ann.get('slice') != current_slice:
                new_data.append(ann)
        
        for shape in shapes:
            shape_type = shape.get('type')
            if shape_type in ['path', 'circle', 'rect', 'line']:
                ann = {
                    'id': f"MANUAL-{str(uuid.uuid4())[:8].upper()}",
                    'slice': current_slice,
                    'type': shape_type,
                    'loc': 'Dessin manuel',
                    'size': 'N/A',
                    'note': ''
                }
                if shape_type in ['path', 'line']:
                    ann['path'] = shape.get('path', '')
                else:
                    ann['x0'] = shape.get('x0')
                    ann['y0'] = shape.get('y0')
                    ann['x1'] = shape.get('x1')
                    ann['y1'] = shape.get('y1')
                new_data.append(ann)
        return new_data

    @app.callback(
        Output('2d-viewer-graph', 'figure'),
        Output('slice-display', 'children'),
        Input('slice-slider', 'value'),
        Input('annotations-store', 'data'),
        Input('selected-anomaly-store', 'data')
    )
    def update_slice_display(slice_idx, store_data, selected_anomaly):
        """
        Update the 2D viewer graph to display the correct slice image 
        along with its corresponding annotations.
        """
        if slice_idx is None:
            slice_idx = 1
            
        z = slice_idx - 1
        if z < 0 or z >= segmenter.lung.shape[0]:
            z = 0

        # Add shapes for current slice
        shapes = []
        for ann in store_data:
            z_range = ann.get('z_range')
            if z_range:
                visible = z_range[0] + 1 <= slice_idx <= z_range[1] + 1
            else:
                visible = ann.get('slice') == slice_idx

            if not visible:
                continue

            if ann.get('slice') == slice_idx:
                color = "yellow" if selected_anomaly == ann['id'] else "cyan"
                
                shape_dict = dict(
                    type=ann.get('type', 'path'),
                    line_color=color,
                    opacity=0.8,
                    line_width=2
                )
                if ann.get('type') in ['path', 'line'] or 'path' in ann:
                    shape_dict['path'] = ann.get('path', '')
                else:
                    shape_dict['x0'] = ann.get('x0')
                    shape_dict['y0'] = ann.get('y0')
                    shape_dict['x1'] = ann.get('x1')
                    shape_dict['y1'] = ann.get('y1')
                shapes.append(shape_dict)

        # Check what triggered the callback
        triggered_ids = [t['prop_id'].split('.')[0] for t in ctx.triggered]
        
        if 'slice-slider' not in triggered_ids and ('annotations-store' in triggered_ids or 'selected-anomaly-store' in triggered_ids):
            # Partial update to avoid sending image data over network
            patched_fig = Patch()
            patched_fig['layout']['shapes'] = shapes
            return patched_fig, no_update

        slice_img = segmenter.lung[z, :, :]
        
        patched_fig = Patch()
        patched_fig['data'][0]['z'] = slice_img
        patched_fig['layout']['shapes'] = shapes
        
        return patched_fig, f"Slice {slice_idx}/{segmenter.lung.shape[0]}"

    @app.callback(
        Output('vtk-container', 'children'),
        Output('ann-count-store', 'data', allow_duplicate=True),
        Input('current-3d-model', 'data'),
        State('slice-slider', 'value'),
        State('annotations-store', 'data'),
        State('selected-anomaly-store', 'data'),
        prevent_initial_call=True
    )
    def update_vtk_volume(model_data, slice_z, annotations, selected_anomaly):
        """
        Rebuild the 3D VTK view ONLY when the underlying 3D model changes.
        """
        import dash_vtk
        
        if model_data and "volume" in model_data:
            volume_data = model_data["volume"]
            dims = model_data["dimensions"]
            spacing = model_data["spacing"]
            
            vtk_children = [
                dash_vtk.VolumeRepresentation(
                    id="main-volume-repr",
                    mapper={"colorBlendMode": 0},
                    colorMapPreset="Grayscale",
                    colorDataRange=[0, 255],
                    children=[
                        dash_vtk.VolumeController(id="main-volume-ctrl"),
                        dash_vtk.ImageData(
                            id="main-volume-img",
                            dimensions=dims,
                            origin=[0, 0, 0],
                            spacing=spacing,
                            children=[
                                dash_vtk.PointData([
                                    dash_vtk.DataArray(
                                        registration="setScalars",
                                        type="Uint8Array",
                                        values=volume_data
                                    )
                                ])
                            ]
                        )
                    ]
                )
            ]
            
            if slice_z:
                z_idx = slice_z - 1
                z_pos = z_idx * spacing[2]
                X = dims[0] * spacing[0]
                Y = dims[1] * spacing[1]
                slice_pts = [0, 0, z_pos, X, 0, z_pos, X, Y, z_pos, 0, Y, z_pos]
                slice_polys = [4, 0, 1, 2, 3]
                
                vtk_children.append(
                    dash_vtk.GeometryRepresentation(
                        id="slice-plane-repr",
                        property={"color": [0, 1, 1], "lineSegment": True, "lineWidth": 2, "opacity": 0.8},
                        children=[dash_vtk.PolyData(id="slice-plane-poly", points=slice_pts, polys=slice_polys)]
                    )
                )
                
            triggerRender = 0
            
            ann_reps = _build_vtk_annotations_list(annotations, selected_anomaly, model_data)
            vtk_children.extend(ann_reps)
            ann_count = len(ann_reps)
        else:
            vtk_children = [
                dash_vtk.GeometryRepresentation(
                    id="lung-mesh-repr",
                    property={"color": [1, 1, 1], "opacity": 0.15, "edgeVisibility": False},
                    children=[dash_vtk.PolyData(points=lung_points, polys=lung_polys)]
                ),
                dash_vtk.GeometryRepresentation(id="slice-plane-repr")
            ]
            triggerRender = 1
            ann_count = 0

        view_component = dash_vtk.View(
            id="vtk-view",
            background=[0, 0, 0],
            style={"width": "100%", "height": "100%", "flex": 1},
            triggerRender=triggerRender,
            children=vtk_children
        )
                
        return [view_component], ann_count

    @app.callback(
        Output('vtk-view', 'children'),
        Output('ann-count-store', 'data'),
        Input('annotations-store', 'data'),
        Input('selected-anomaly-store', 'data'),
        Input('current-3d-model', 'data'),
        State('ann-count-store', 'data'),
        prevent_initial_call=True
    )
    def update_vtk_annotations(store_data, selected_anomaly, model_data, ann_count):
        """
        Dynamically append/remove annotations using Patch(), leaving the VolumeRepresentation untouched.
        This prevents resetting user settings ('Use shadow', 'Rainbow').
        """
        import dash
        import dash_vtk
        import math
        
        triggered_ids = [t['prop_id'].split('.')[0] for t in dash.callback_context.triggered]
        if 'current-3d-model' in triggered_ids:
            return dash.no_update, dash.no_update
        
        patch = Patch()
        ann_count = ann_count or 0
        
        # Remove previous annotations from the Patch array
        for _ in range(ann_count):
            del patch[-1]
            
        ann_reps = _build_vtk_annotations_list(store_data, selected_anomaly, model_data)
        for rep in ann_reps:
            patch.append(rep)
                    
        return patch, len(ann_reps)

    @app.callback(
        Output('slice-plane-poly', 'points'),
        Input('slice-slider', 'value'),
        State('current-3d-model', 'data'),
        prevent_initial_call=True
    )
    def fast_update_slice_highlight(slice_z, model_data):
        if not model_data or "spacing" not in model_data or not slice_z:
            return no_update
            
        spacing = model_data["spacing"]
        dims = model_data["dimensions"]
        
        z_idx = slice_z - 1
        z_pos = z_idx * spacing[2]
        
        X = dims[0] * spacing[0]
        Y = dims[1] * spacing[1]
        
        slice_pts = [
            0, 0, z_pos,
            X, 0, z_pos,
            X, Y, z_pos,
            0, Y, z_pos
        ]
        
        return slice_pts

    @app.callback(
        Output('anomalies-list', 'children'),
        Input('annotations-store', 'data'),
        Input('anomaly-search-input', 'value')
    )
    def update_cards(store_data, search_text):
        """
        Update the list of anomaly cards and filter them based on search input.
        """
        if not store_data:
            return []
            
        cards = []
        search_text = (search_text or "").lower()
        
        for ann in store_data:
            ann_name = ann.get('id', '').lower()
            ann_slice = str(ann.get('slice', ''))
            
            # Simple filter
            if search_text in ann_name or search_text in ann_slice or search_text == "":
                cards.append(anomaly_card(ann))
                
        return cards

    @app.callback(
        Output('selected-anomaly-store', 'data'),
        Output('slice-slider', 'value'),
        Input({'type': 'anomaly-card', 'index': ALL}, 'n_clicks'),
        State('annotations-store', 'data'),
        State('slice-slider', 'value'),
        prevent_initial_call=True
    )
    def select_anomaly(n_clicks_list, store_data, current_slice):
        """
        Handle clicks on anomaly cards to select them and update the 
        slice slider to the anomaly's location.
        """
        if not ctx.triggered:
            return no_update, current_slice
            
        triggered_input = ctx.triggered[0]
        if triggered_input['value'] is None or triggered_input['value'] == 0:
            return no_update, current_slice
            
        triggered_id = ctx.triggered_id
        if triggered_id and triggered_id.get('type') == 'anomaly-card':
            ann_id = triggered_id.get('index')
            # Find slice for this anomaly
            for ann in store_data:
                if ann.get('id') == ann_id:
                    return ann_id, ann.get('slice', current_slice)
                    
        return no_update, current_slice

    @app.callback(
        Output('annotations-store', 'data', allow_duplicate=True),
        Input({'type': 'delete-anomaly', 'index': ALL}, 'n_clicks'),
        State('annotations-store', 'data'),
        prevent_initial_call=True
    )
    def delete_anomaly(n_clicks_list, store_data):
        """
        Handle clicks on the trash icon to delete an anomaly from the store.
        """
        if not ctx.triggered:
            return no_update
            
        triggered_input = ctx.triggered[0]
        if triggered_input['value'] is None or triggered_input['value'] == 0:
            return no_update
            
        triggered_id = ctx.triggered_id
        if triggered_id and triggered_id.get('type') == 'delete-anomaly':
            ann_id = triggered_id.get('index')
            new_data = []
            for ann in store_data:
                if ann.get('id') != ann_id:
                    new_data.append(ann)
            return new_data
            
        return no_update

    @app.callback(
        Output('2d-empty-state', 'style'),
        Output('2d-viewer-container', 'style'),
        Output('slice-slider', 'max'),
        Output('slice-slider', 'value', allow_duplicate=True),
        Input('current-3d-model', 'data'),
        prevent_initial_call=True
    )
    def toggle_2d_viewer(model_data):
        if not model_data:
            return {"width": "100%", "height": "100%", "display": "flex", "padding": "20px", "flex": 1}, {"display": "none"}, no_update, no_update
        
        max_slice = model_data.get("dimensions", [0, 0, 1])[2]
        mid_slice = max(1, max_slice // 2)
        return {"display": "none"}, {"width": "100%", "height": "100%", "display": "flex", "flex": 1}, max_slice, mid_slice

    @app.callback(
        Output('upload-content-store', 'data'),
        Input('upload-dicom', 'contents'),
        Input('upload-dicom-2d', 'contents'),
        prevent_initial_call=True
    )
    def handle_upload(contents1, contents2):
        if not ctx.triggered:
            return no_update
        contents = ctx.triggered[0]['value']
        if contents:
            return contents
        return no_update

    @app.callback(
        Output('patient-modal', 'opened'),
        Input('upload-content-store', 'data'),
        prevent_initial_call=True
    )
    def open_modal_on_upload(contents):
        if contents:
            return True
        return False

    @app.callback(
        Output('patients-store', 'data'),
        Output('current-3d-model', 'data'),
        Output('annotations-store', 'data', allow_duplicate=True),
        Output('patient-modal', 'opened', allow_duplicate=True),
        Input('submit-patient-btn', 'n_clicks'),
        State('patient-name-input', 'value'),
        State('patient-age-input', 'value'),
        State('patient-sex-input', 'value'),
        State('upload-content-store', 'data'),
        State('patients-store', 'data'),
        State('annotations-store', 'data'),
        prevent_initial_call=True
    )
    def process_dicom_upload(n_clicks, name, age, sex, contents, patients_data, annotations_data):
        if not n_clicks or not contents:
            return no_update, no_update, no_update, no_update
            
        import base64
        import os
        import requests
        import zipfile
        import uuid
        
        # Save ZIP
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "storage"))
        uploads_dir = os.path.join(STORAGE_DIR, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        
        patient_id = f"PAT-{str(uuid.uuid4())[:8].upper()}"
        patient_dir = os.path.join(uploads_dir, patient_id)
        os.makedirs(patient_dir, exist_ok=True)
        
        zip_path = os.path.join(patient_dir, "upload.zip")
        with open(zip_path, "wb") as f:
            f.write(decoded)
            
        # Unzip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(patient_dir)
            
        # Call Backend
        resp_data = _call_backend(patient_id) or {"error": "backend unreachable"}
        new_annotations = _apply_resp_data(resp_data)
            
        # Add patient to store
        new_patient = {
            "id": patient_id,
            "name": name or "Inconnu",
            "age": age,
            "sex": sex,
            "date": "Aujourd'hui"
        }
        patients_data.append(new_patient)

        # Return patients, the 3d model data, annotations and close modal
        return patients_data, resp_data, annotations_data + new_annotations, False

    @app.callback(
        Output('patients-list', 'children'),
        Input('patients-store', 'data')
    )
    def render_patients(patients_data):
        from components.cards import patient_card
        cards = []
        for p in patients_data:
            cards.append(patient_card(p))
        return cards

    @app.callback(
        Output('traces-container', 'children'),
        Input('annotations-store', 'data')
    )
    def update_traces_info(annotations):
        import dash_mantine_components as dmc
        manual_traces = [a for a in annotations if a.get('loc') == 'Dessin manuel']
        if not manual_traces:
            return dmc.Text("Aucun tracé manuel en cours", c="dimmed", size="sm")
        
        return dmc.Stack(
            gap="xs",
            children=[
                dmc.Text(f"{len(manual_traces)} tracés manuels", fw=500, size="sm"),
                dmc.Text("Volume total estimé : Non calculé", size="xs", c="dimmed")
            ]
        )

    @app.callback(
        Output('report-modal', 'opened'),
        Output('report-content', 'children'),
        Input('open-report-btn', 'n_clicks'),
        Input('close-report-btn', 'n_clicks'),
        State('patients-store', 'data'),
        State('annotations-store', 'data'),
        prevent_initial_call=True
    )
    def handle_report_modal(open_clicks, close_clicks, patients, annotations):
        import dash
        ctx = dash.callback_context
        if not ctx.triggered:
            return False, dash.no_update
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'close-report-btn':
            return False, dash.no_update
            
        import dash_mantine_components as dmc
        from dash import html
        
        patient = patients[-1] if patients else {"name": "Inconnu", "age": "N/A", "sex": "N/A"}
        
        auto_anomalies = [a for a in annotations if a.get('loc') == 'Backend']
        manual_traces = [a for a in annotations if a.get('loc') == 'Dessin manuel']
        
        content = dmc.Stack(
            gap="sm",
            children=[
                dmc.Title(f"Rapport d'imagerie - {patient.get('name')}", order=3),
                dmc.Group(
                    gap="xl",
                    children=[
                        dmc.Text(f"Sexe: {patient.get('sex', 'N/A')}", size="sm"),
                        dmc.Text(f"Âge: {patient.get('age', 'N/A')} ans", size="sm"),
                    ]
                ),
                dmc.Divider(my="sm"),
                dmc.Text("Anomalies détectées par l'IA :", fw=600),
                html.Ul([html.Li(f"Coupe {a['slice']} - Taille: {a.get('size', 'N/A')} - {a.get('note', '')}") for a in auto_anomalies]) if auto_anomalies else dmc.Text("Aucune anomalie détectée", size="sm", c="dimmed"),
                dmc.Text("Tracés manuels du praticien :", fw=600, mt="md"),
                html.Ul([html.Li(f"Tracé sur coupe {a['slice']}") for a in manual_traces]) if manual_traces else dmc.Text("Aucun tracé manuel", size="sm", c="dimmed"),
                dmc.Divider(my="sm"),
                dmc.Text("Conclusion Médicale :", fw=600),
                dmc.Textarea(placeholder="Tapez la conclusion de l'examen ici avant impression...", minRows=4, w="100%", autosize=True)
            ]
        )
        
        return True, content

    # Clientside callback to trigger browser print
    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks) {
                window.print();
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('print-report-btn', 'disabled'),
        Input('print-report-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    
    @app.callback(
        Output('current-3d-model', 'data', allow_duplicate=True),
        Output('annotations-store', 'data', allow_duplicate=True),
        Input({'type': 'patient-card', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def switch_patient(n_clicks_list):
        if not ctx.triggered or ctx.triggered[0]['value'] in (None, 0):
            return no_update, no_update

        import json
        triggered_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        patient_id = triggered_id['index']

        resp_data = _call_backend(patient_id)
        if not resp_data:
            return no_update, no_update

        return resp_data, _apply_resp_data(resp_data)
