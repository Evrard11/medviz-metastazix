from dash import Input, Output, State, ALL, ctx, no_update, Patch
from core import app
import dash_vtk
import plotly.express as px
import uuid
import math
from data.backend_integration import segmenter, lung_points, lung_polys
from components.cards import anomaly_card
from utils.parsing_utils import svg_path_to_vtk_polydata

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
        triggered_id = getattr(ctx, 'triggered_id', None)
        
        if triggered_id in ['annotations-store', 'selected-anomaly-store']:
            # Partial update to avoid sending image data over network
            patched_fig = Patch()
            patched_fig['layout']['shapes'] = shapes
            return patched_fig, no_update

        # Full update (slice changed)
        # Get slice image
        slice_img = segmenter.lung[z, :, :]
        
        fig = px.imshow(slice_img, color_continuous_scale='gray', template="plotly_dark")
        fig.update_layout(
            dragmode="drawclosedpath",
            newshape=dict(line_color="cyan", opacity=0.8, line_width=2),
            margin=dict(l=0, r=0, b=0, t=0),
            coloraxis_showscale=False,
            xaxis=dict(showticklabels=False),
            yaxis=dict(showticklabels=False)
        )
        
        fig.update_layout(shapes=shapes)
        return fig, f"Slice {slice_idx}/{segmenter.lung.shape[0]}"

    @app.callback(
        Output('vtk-view', 'children'),
        Output('anomalies-list', 'children'),
        Input('annotations-store', 'data'),
        Input('selected-anomaly-store', 'data')
    )
    def update_vtk_and_cards(store_data, selected_anomaly):
        """
        Update the 3D VTK view and the list of anomaly cards based on the 
        current annotations and selected anomaly.
        """
        cards = []
        for ann in store_data:
            cards.append(anomaly_card(ann))
        
        # Lung mesh
        vtk_children = [
            dash_vtk.GeometryRepresentation(
                property={"color": [1, 1, 1], "opacity": 0.15, "edgeVisibility": False},
                children=[
                    dash_vtk.PolyData(points=lung_points, polys=lung_polys)
                ]
            )
        ]
        
        # Drawn polygons
        for ann in store_data:
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
                cx, cy = (x0+x1)/2, (y0+y1)/2
                rx, ry = abs(x1-x0)/2, abs(y1-y0)/2
                pts = []
                for i in range(16):
                    ang = i * math.pi / 8
                    pts.append(f"{cx + rx*math.cos(ang)},{cy + ry*math.sin(ang)}")
                path_str = f"M {pts[0]} " + " ".join([f"L {p}" for p in pts[1:]]) + " Z"
                
            if path_str:
                pts, polys = svg_path_to_vtk_polydata(path_str, ann['slice'] - 1)
                color = [1, 1, 0] if selected_anomaly == ann['id'] else [1, 0, 0]
                vtk_children.append(
                    dash_vtk.GeometryRepresentation(
                        property={"color": color, "lineSegment": True, "lineWidth": 3},
                        children=[
                            dash_vtk.PolyData(points=pts, polys=polys)
                        ]
                    )
                )
                
        return vtk_children, cards

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
