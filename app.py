import os
import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from dash.dependencies import Input, Output, State
from pymongo import MongoClient
from urllib.parse import quote_plus
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB Credentials from environment variables
MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST")
DATABASE_NAME = os.getenv("DATABASE_NAME")

# Encode credentials
encoded_username = quote_plus(MONGO_USERNAME)
encoded_password = quote_plus(MONGO_PASSWORD)

# Construct MongoDB URI
MONGO_URI = f"mongodb+srv://{encoded_username}:{encoded_password}@{MONGO_HOST}/?retryWrites=true&w=majority"

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
warehouses_collection = db["Warehouses"]
transporting_collection = db["Transporting"]

# Custom color schemes
COLORS = {
    'warehouse': px.colors.sequential.Blues_r,
    'transport': px.colors.sequential.Oranges_r,
    'background': '#121212',
    'card_bg': '#1E1E2E',
    'text': '#FFFFFF',
    'accent': '#4B9CD3',
    'success': '#4CAF50',
    'warning': '#FF9800',
    'danger': '#F44336',
    'info': '#2196F3'
}

# Fetch data from MongoDB
def get_warehouse_data():
    data = list(warehouses_collection.find())
    return pd.DataFrame(data)

def get_transporting_data():
    data = list(transporting_collection.find())
    return pd.DataFrame(data)

# Initialize Dash app with a more modern theme
external_stylesheets = [
    dbc.themes.DARKLY,
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css",
]

app = dash.Dash(
    __name__, 
    external_stylesheets=external_stylesheets,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)
server = app.server

# Custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>ERP Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            .dashboard-card {
                border-radius: 15px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
                margin-bottom: 20px;
                transition: all 0.3s ease;
            }
            .dashboard-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            }
            .kpi-card {
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                transition: all 0.3s ease;
            }
            .kpi-card:hover {
                transform: scale(1.05);
            }
            .kpi-value {
                font-size: 2rem;
                font-weight: bold;
            }
            .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner table {
                border-radius: 10px;
                overflow: hidden;
            }
            /* Custom scrollbar */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            ::-webkit-scrollbar-track {
                background: #1E1E2E;
            }
            ::-webkit-scrollbar-thumb {
                background: #4B9CD3;
                border-radius: 4px;
            }
            ::-webkit-scrollbar-thumb:hover {
                background: #2979b5;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Function to create a styled KPI card
def create_kpi_card(title, value, icon, color):
    return dbc.Card(
        dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon} fa-2x mb-2", style={"color": color}),
                html.H6(title, className="text-muted"),
                html.Div(value, className="kpi-value", style={"color": color}),
            ], className="text-center")
        ]),
        className="kpi-card",
        style={"backgroundColor": COLORS['card_bg'], "border": f"1px solid {color}"}
    )

# App layout using Bootstrap components for a modern, responsive design
app.layout = dbc.Container([
    # Header with navigation
    dbc.Navbar(
        dbc.Container([
            html.A(
                dbc.Row([
                    dbc.Col(html.I(className="fas fa-warehouse me-2"), width="auto"),
                    dbc.Col(dbc.NavbarBrand("ERP Logistics Dashboard", className="ms-2"), width="auto"),
                ], align="center", className="g-0"),
                href="#",
                style={"textDecoration": "none"},
            ),
            dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink("Warehouse", href="#warehouse-section")),
                    dbc.NavItem(dbc.NavLink("Transport", href="#transport-section")),
                    dbc.NavItem(dbc.NavLink("Analytics", href="#analytics-section")),
                ], className="ms-auto", navbar=True),
                id="navbar-collapse",
                navbar=True,
            ),
        ], fluid=True),
        color="dark",
        dark=True,
        sticky="top",
        className="mb-4",
    ),
    
    # Dashboard header
    dbc.Row([
        dbc.Col([
            html.H1([
                html.I(className="fas fa-chart-line me-3"), 
                "Supply Chain Analytics"
            ], className="text-center text-light mb-4"),
            html.P("Real-time inventory and logistics monitoring system", 
                  className="text-center text-muted mb-5"),
        ], width=12)
    ]),
    
    # Summary KPI cards
    dbc.Row([
        dbc.Col(html.Div(id="warehouse-count-kpi"), md=3),
        dbc.Col(html.Div(id="product-count-kpi"), md=3),
        dbc.Col(html.Div(id="transport-count-kpi"), md=3), 
        dbc.Col(html.Div(id="utilization-kpi"), md=3),
    ], className="mb-4"),
    
    # Filter and time controls
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5("Dashboard Controls", className="card-title mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Label("Refresh Rate", className="text-muted"),
                            dcc.Dropdown(
                                id='refresh-rate',
                                options=[
                                    {'label': '30 seconds', 'value': 30000},
                                    {'label': '1 minute', 'value': 60000},
                                    {'label': '5 minutes', 'value': 300000},
                                ],
                                value=60000,
                                clearable=False,
                                style={"backgroundColor": "#2C2C44", "color": "#333"}
                            ),
                        ], md=4),
                        dbc.Col([
                            html.Label("View Mode", className="text-muted"),
                            dbc.RadioItems(
                                id='view-mode',
                                options=[
                                    {'label': 'Detailed', 'value': 'detailed'},
                                    {'label': 'Summary', 'value': 'summary'},
                                ],
                                value='detailed',
                                inline=True,
                                className="mt-1"
                            ),
                        ], md=4),
                        dbc.Col([
                            html.Label("Last Updated", className="text-muted"),
                            html.Div(id="last-updated", className="mt-1"),
                        ], md=4),
                    ]),
                ]),
            ], className="dashboard-card", style={"backgroundColor": COLORS['card_bg']}),
        ], width=12),
    ], className="mb-4"),
    
    # Warehouse Section
    html.Div([
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-box me-2"), 
                    "Warehouse Inventory"
                ], className="text-info mb-4", id="warehouse-section"),
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col(dcc.Graph(id='warehouse_heatmap', config={'displayModeBar': False}), md=8),
                            dbc.Col(dcc.Graph(id='warehouse_pie_chart', config={'displayModeBar': False}), md=4),
                        ]),
                    ]),
                ], className="dashboard-card mb-3", style={"backgroundColor": COLORS['card_bg']}),
                
                # Warehouse detailed data
                html.Div(id="warehouse-detailed-view"),
            ], width=12),
        ]),
    ], className="mb-5"),
    
    # Transport Section
    html.Div([
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-truck me-2"), 
                    "Transport Analytics"
                ], className="text-warning mb-4", id="transport-section"),
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col(dcc.Graph(id='transport_bar_chart', config={'displayModeBar': False}), md=7),
                            dbc.Col(dcc.Graph(id='transport_gauge_chart', config={'displayModeBar': False}), md=5),
                        ]),
                    ]),
                ], className="dashboard-card mb-3", style={"backgroundColor": COLORS['card_bg']}),
                
                # Transport detailed data
                html.Div(id="transport-detailed-view"),
            ], width=12),
        ]),
    ], className="mb-5"),
    
    # Analytics Section
    html.Div([
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-chart-area me-2"), 
                    "Comparative Analytics"
                ], className="text-success mb-4", id="analytics-section"),
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(id='combined_analytics', config={'displayModeBar': 'hover'}),
                    ]),
                ], className="dashboard-card", style={"backgroundColor": COLORS['card_bg']}),
            ], width=12),
        ]),
    ]),
    
    # Footer
    html.Footer([
        html.Hr(),
        html.P("© 2025 ERP Logistics Dashboard - Updated in real-time from MongoDB Atlas", 
              className="text-center text-muted"),
    ], className="mt-5"),
    
    # Interval component for refreshing
    dcc.Interval(
        id='interval-component',
        interval=60000,  # Default refresh every 60 seconds
        n_intervals=0
    ),
    
    # Store component for holding data
    dcc.Store(id='warehouse-data-store'),
    dcc.Store(id='transport-data-store'),
    
], fluid=True, style={"backgroundColor": COLORS['background'], "padding": "20px", "minHeight": "100vh"})

# Callback to update the refresh interval
@app.callback(
    Output('interval-component', 'interval'),
    [Input('refresh-rate', 'value')]
)
def update_refresh_interval(value):
    return value

# Callback to update data stores
@app.callback(
    [Output('warehouse-data-store', 'data'),
     Output('transport-data-store', 'data'),
     Output('last-updated', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_data_stores(n):
    warehouse_df = get_warehouse_data()
    transport_df = get_transporting_data()
    
    # Process warehouse data
    if not warehouse_df.empty:
        warehouse_df = warehouse_df.fillna(0)
        product_columns = [col for col in warehouse_df.columns if col.startswith('product')]
        for col in product_columns:
            warehouse_df[col] = pd.to_numeric(warehouse_df[col], errors='coerce').fillna(0)
    
    # Process transport data
    if not transport_df.empty:
        transport_df = transport_df.fillna(0)
        product_columns_transport = [col for col in transport_df.columns if col.startswith('product')]
        for col in product_columns_transport:
            transport_df[col] = pd.to_numeric(transport_df[col], errors='coerce').fillna(0)
    
    # Current timestamp
    now = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    
    return (warehouse_df.to_dict('records') if not warehouse_df.empty else [],
            transport_df.to_dict('records') if not transport_df.empty else [],
            [html.I(className="fas fa-sync-alt me-2"), now])

# Callback to update KPI cards
@app.callback(
    [Output('warehouse-count-kpi', 'children'),
     Output('product-count-kpi', 'children'),
     Output('transport-count-kpi', 'children'),
     Output('utilization-kpi', 'children')],
    [Input('warehouse-data-store', 'data'),
     Input('transport-data-store', 'data')]
)
def update_kpi_cards(warehouse_data, transport_data):
    # Convert data back to DataFrames
    warehouse_df = pd.DataFrame(warehouse_data) if warehouse_data else pd.DataFrame()
    transport_df = pd.DataFrame(transport_data) if transport_data else pd.DataFrame()
    
    # Calculate KPIs
    warehouse_count = len(warehouse_df) if not warehouse_df.empty else 0
    
    product_columns = [col for col in warehouse_df.columns if col.startswith('product')] if not warehouse_df.empty else []
    product_count = len(product_columns)
    
    transport_count = len(transport_df) if not transport_df.empty else 0
    
    # Calculate warehouse utilization (simplified example)
    if not warehouse_df.empty and product_count > 0:
        total_capacity = warehouse_count * product_count * 100  # Assuming 100 is max capacity per product
        current_usage = warehouse_df[product_columns].sum().sum() if not warehouse_df.empty else 0
        utilization = min(100, int((current_usage / total_capacity) * 100)) if total_capacity > 0 else 0
    else:
        utilization = 0
    
    # Create KPI cards
    warehouse_kpi = create_kpi_card("Warehouses", f"{warehouse_count}", "fa-warehouse", COLORS['info'])
    product_kpi = create_kpi_card("Products", f"{product_count}", "fa-box", COLORS['success'])
    transport_kpi = create_kpi_card("Transports", f"{transport_count}", "fa-truck", COLORS['warning'])
    utilization_kpi = create_kpi_card("Utilization", f"{utilization}%", "fa-tachometer-alt", 
                                      COLORS['danger'] if utilization > 90 else 
                                      COLORS['warning'] if utilization > 70 else COLORS['success'])
    
    return warehouse_kpi, product_kpi, transport_kpi, utilization_kpi

# Callback to update warehouse visualizations
@app.callback(
    [Output('warehouse_heatmap', 'figure'),
     Output('warehouse_pie_chart', 'figure'),
     Output('warehouse-detailed-view', 'children')],
    [Input('warehouse-data-store', 'data'),
     Input('view-mode', 'value')]
)
def update_warehouse_visualizations(warehouse_data, view_mode):
    warehouse_df = pd.DataFrame(warehouse_data) if warehouse_data else pd.DataFrame()
    
    if warehouse_df.empty:
        empty_fig = px.bar(title="No Warehouse Data Available")
        empty_fig.update_layout(
            plot_bgcolor=COLORS['card_bg'],
            paper_bgcolor=COLORS['card_bg'],
            font=dict(color=COLORS['text']),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        return empty_fig, empty_fig, html.Div("No data available")
    
    product_columns = [col for col in warehouse_df.columns if col.startswith('product')]
    
    # Create a heatmap for warehouse product levels
    heatmap_df = warehouse_df.melt(
        id_vars=['_id'], 
        value_vars=product_columns,
        var_name='Product',
        value_name='Quantity'
    )
    
    # Clean product names for better display
    heatmap_df['Product'] = heatmap_df['Product'].str.replace('product', 'Product ')
    
    warehouse_heatmap = px.density_heatmap(
        heatmap_df,
        x='_id',
        y='Product',
        z='Quantity',
        title="Warehouse Inventory Heatmap",
        color_continuous_scale=COLORS['warehouse'],
        labels={'_id': 'Warehouse ID', 'Quantity': 'Stock Level'}
    )
    
    warehouse_heatmap.update_layout(
        plot_bgcolor=COLORS['card_bg'],
        paper_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text']),
        margin=dict(l=40, r=40, t=40, b=40),
        coloraxis_colorbar=dict(
            title="Stock Level",
            tickfont=dict(color=COLORS['text']),
            title_font=dict(color=COLORS['text'])  # Corrected property name
        ),
    )
    # Summarize total stock across warehouses for each product
    warehouse_sum = warehouse_df[product_columns].sum()
    warehouse_sum.index = warehouse_sum.index.str.replace('product', 'Product ')
    
    warehouse_pie_chart = px.pie(
        names=warehouse_sum.index,
        values=warehouse_sum.values,
        title="Product Distribution",
        color_discrete_sequence=COLORS['warehouse'],
        hole=0.4,
    )
    
    warehouse_pie_chart.update_layout(
        plot_bgcolor=COLORS['card_bg'],
        paper_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text']),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            font=dict(color=COLORS['text']),
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )
    
    # Create detailed view with table if detailed mode is selected
    if view_mode == 'detailed':
        # Prepare data for table - clean column names for better display
        table_df = warehouse_df.copy()
        table_df.columns = [col.replace('product', 'Product ') if col.startswith('product') else col 
                           for col in table_df.columns]
        
        detailed_view = dbc.Card([
            dbc.CardHeader(html.H5("Warehouse Inventory Details", className="card-title")),
            dbc.CardBody([
                dash_table.DataTable(
                    id='warehouse_table',
                    data=table_df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in table_df.columns],
                    style_table={'overflowX': 'auto'},
                    page_size=5,
                    style_cell={
                        'textAlign': 'center',
                        'padding': '10px',
                        'backgroundColor': COLORS['card_bg'],
                        'color': COLORS['text'],
                    },
                    style_header={
                        'backgroundColor': '#2B2B3F',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'textAlign': 'center',
                    },
                    style_data_conditional=[
                        {
                            'if': {'column_type': 'numeric'},
                            'textAlign': 'right'
                        },
                        {
                            'if': {
                                'filter_query': '{Quantity} < 20',
                                'column_id': 'Quantity'
                            },
                            'color': COLORS['danger'],
                            'fontWeight': 'bold'
                        }
                    ],
                    sort_action='native',
                    filter_action='native',
                    row_selectable='multi',
                )
            ]),
        ], className="dashboard-card", style={"backgroundColor": COLORS['card_bg']})
    else:
        # Create a summary view with top/bottom performing warehouses
        product_totals = warehouse_df[product_columns].sum(axis=1)
        warehouse_df['total_stock'] = product_totals
        top_warehouses = warehouse_df.nlargest(3, 'total_stock')
        bottom_warehouses = warehouse_df.nsmallest(3, 'total_stock')
        
        detailed_view = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Top Stocked Warehouses", className="card-title text-success")),
                    dbc.CardBody([
                        html.Div([
                            html.H6(f"Warehouse: {row['_id']}", className="mb-2"),
                            dbc.Progress(
                                value=int(row['total_stock']), 
                                max=warehouse_df['total_stock'].max(),
                                color="success",
                                className="mb-3",
                                style={"height": "20px"},
                                label=f"{int(row['total_stock'])} units"
                            )
                        ]) for i, row in top_warehouses.iterrows()
                    ]),
                ], className="dashboard-card h-100", style={"backgroundColor": COLORS['card_bg']}),
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Low Stock Warehouses", className="card-title text-danger")),
                    dbc.CardBody([
                        html.Div([
                            html.H6(f"Warehouse: {row['_id']}", className="mb-2"),
                            dbc.Progress(
                                value=int(row['total_stock']), 
                                max=warehouse_df['total_stock'].max(),
                                color="danger",
                                className="mb-3",
                                style={"height": "20px"},
                                label=f"{int(row['total_stock'])} units"
                            )
                        ]) for i, row in bottom_warehouses.iterrows()
                    ]),
                ], className="dashboard-card h-100", style={"backgroundColor": COLORS['card_bg']}),
            ], md=6),
        ])
    
    return warehouse_heatmap, warehouse_pie_chart, detailed_view

# Callback to update transport visualizations
@app.callback(
    [Output('transport_bar_chart', 'figure'),
     Output('transport_gauge_chart', 'figure'),
     Output('transport-detailed-view', 'children')],
    [Input('transport-data-store', 'data'),
     Input('view-mode', 'value')]
)
def update_transport_visualizations(transport_data, view_mode):
    transport_df = pd.DataFrame(transport_data) if transport_data else pd.DataFrame()
    
    if transport_df.empty:
        empty_fig = px.bar(title="No Transport Data Available")
        empty_fig.update_layout(
            plot_bgcolor=COLORS['card_bg'],
            paper_bgcolor=COLORS['card_bg'],
            font=dict(color=COLORS['text']),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        return empty_fig, empty_fig, html.Div("No data available")
    
    product_columns = [col for col in transport_df.columns if col.startswith('product')]
    
    # Melt the dataframe for visualization
    transport_melted = transport_df.melt(
        id_vars=['_id'],
        value_vars=product_columns,
        var_name='Product',
        value_name='Quantity'
    )
    
    # Clean product names for better display
    transport_melted['Product'] = transport_melted['Product'].str.replace('product', 'Product ')
    
    # Create a bar chart with custom styling
    transport_bar_chart = px.bar(
        transport_melted,
        x='_id',
        y='Quantity',
        color='Product',
        title="Transport Shipment Volumes",
        barmode='group',
        color_discrete_sequence=COLORS['transport'],
        labels={'_id': 'Transport ID', 'Quantity': 'Units in Transit'},
        text='Quantity'
    )
    
    transport_bar_chart.update_traces(
        textposition='outside',
        texttemplate='%{text:.0f}'
    )
    
    transport_bar_chart.update_layout(
        plot_bgcolor=COLORS['card_bg'],
        paper_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text']),
        margin=dict(l=40, r=40, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Create a gauge chart showing total transport utilization
    transport_sum = transport_df[product_columns].sum().sum()
    max_capacity = len(transport_df) * len(product_columns) * 100  # Assuming 100 is max capacity
    utilization_percent = min(100, (transport_sum / max_capacity) * 100) if max_capacity > 0 else 0
    
    transport_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=utilization_percent,
        title={'text': "Transport Fleet Utilization", 'font': {'color': COLORS['text']}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': COLORS['text']},
            'bar': {'color': COLORS['warning']},
            'steps': [
                {'range': [0, 30], 'color': 'rgba(0, 128, 0, 0.3)'},
                {'range': [30, 70], 'color': 'rgba(255, 165, 0, 0.3)'},
                {'range': [70, 100], 'color': 'rgba(255, 0, 0, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        },
        number={'font': {'color': COLORS['text']}, 'suffix': '%'}
    ))
    
    transport_gauge.update_layout(
        plot_bgcolor=COLORS['card_bg'],
        paper_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text']),
        margin=dict(l=40, r=40, t=60, b=20),
    )
    
    # Create detailed view based on selected mode
    if view_mode == 'detailed':
        # Prepare data for table - clean column names for display
        table_df = transport_df.copy()
        table_df.columns = [col.replace('product', 'Product ') if col.startswith('product') else col 
                           for col in table_df.columns]
        
        detailed_view = dbc.Card([
            dbc.CardHeader(html.H5("Transport Shipment Details", className="card-title")),
            dbc.CardBody([
                dash_table.DataTable(
                    id='transport_table',
                    data=table_df.to_dict('records'),
                    columns=[{"name": col, "id": col} for col in table_df.columns],
                    style_table={'overflowX': 'auto'},
                    page_size=5,
                    style_cell={
                        'textAlign': 'center',
                        'padding': '10px',
                        'backgroundColor': COLORS['card_bg'],
                        'color': COLORS['text'],
                    },
                    style_header={
                        'backgroundColor': '#2B2B3F',
                        'color': 'white',
                        'fontWeight': 'bold',
                        'textAlign': 'center',
                    },
                    style_data_conditional=[
                        {
                            'if': {'column_type': 'numeric'},
                            'textAlign': 'right'
                        }
                    ],
                    sort_action='native',
                    filter_action='native',
                )
            ]),
        ], className="dashboard-card", style={"backgroundColor": COLORS['card_bg']})
    else:
        # Create a summary view showing transport efficiency metrics
        product_totals = transport_df[product_columns].sum(axis=1)
        transport_df['total_cargo'] = product_totals
        
        # Calculate some mock efficiency metrics
        max_load = transport_df['total_cargo'].max()
        avg_load = transport_df['total_cargo'].mean()
        efficiency_rate = (avg_load / max_load) * 100 if max_load > 0 else 0
        
        detailed_view = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Transport Load Analysis", className="card-title")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.H6("Average Load", className="text-muted"),
                                html.H3(f"{avg_load:.1f} units", className="text-info"),
                            ], md=6),
                            dbc.Col([
                                html.H6("Maximum Load", className="text-muted"),
                                html.H3(f"{max_load:.1f} units", className="text-warning"),], md=6),
                        ]),
                        html.Hr(),
                        html.H6("Fleet Efficiency Rate", className="mt-3 text-muted"),
                        dbc.Progress(
                            value=efficiency_rate,
                            color="success" if efficiency_rate > 75 else "warning" if efficiency_rate > 50 else "danger",
                            className="mt-2",
                            style={"height": "20px"},
                            label=f"{efficiency_rate:.1f}%"
                        ),
                        html.Div([
                            html.I(className="fas fa-info-circle me-2"),
                            "Efficiency rate shows how close the average load is to maximum capacity"
                        ], className="mt-2 text-muted small"),
                    ]),
                ], className="dashboard-card h-100", style={"backgroundColor": COLORS['card_bg']}),
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Transport Status", className="card-title")),
                    dbc.CardBody([
                        html.Div([
                            dbc.Row([
                                dbc.Col(html.Div([
                                    html.I(className="fas fa-truck fa-2x mb-2", style={"color": COLORS['warning']}),
                                    html.H6("Active Transports", className="text-muted"),
                                    html.H3(f"{len(transport_df)}", className="text-warning"),
                                ], className="text-center"), md=6),
                                dbc.Col(html.Div([
                                    html.I(className="fas fa-box fa-2x mb-2", style={"color": COLORS['info']}),
                                    html.H6("Total Cargo", className="text-muted"),
                                    html.H3(f"{transport_df['total_cargo'].sum():.0f}", className="text-info"),
                                ], className="text-center"), md=6),
                            ], className="mb-4"),
                            html.Hr(),
                            html.H6("Most Active Routes", className="mt-3 text-muted"),
                            # Mock route data - in a real app, you'd calculate this from your data
                            html.Div([
                                html.Div(f"Route {i+1}: Warehouse {chr(65+i)} → Destination {chr(75+i)}",
                                        className="my-2") for i in range(3)
                            ]),
                        ]),
                    ]),
                ], className="dashboard-card h-100", style={"backgroundColor": COLORS['card_bg']}),
            ], md=6),
        ])
    
    return transport_bar_chart, transport_gauge, detailed_view

# Callback to update combined analytics visualization
@app.callback(
    Output('combined_analytics', 'figure'),
    [Input('warehouse-data-store', 'data'),
     Input('transport-data-store', 'data')]
)
def update_combined_analytics(warehouse_data, transport_data):
    warehouse_df = pd.DataFrame(warehouse_data) if warehouse_data else pd.DataFrame()
    transport_df = pd.DataFrame(transport_data) if transport_data else pd.DataFrame()
    
    if warehouse_df.empty or transport_df.empty:
        empty_fig = px.line(title="Insufficient Data for Comparative Analytics")
        empty_fig.update_layout(
            plot_bgcolor=COLORS['card_bg'],
            paper_bgcolor=COLORS['card_bg'],
            font=dict(color=COLORS['text']),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        return empty_fig
    
    # Get product columns from both dataframes
    warehouse_product_cols = [col for col in warehouse_df.columns if col.startswith('product')]
    transport_product_cols = [col for col in transport_df.columns if col.startswith('product')]
    
    # Find common products for analysis
    common_products = list(set(warehouse_product_cols).intersection(set(transport_product_cols)))
    
    if not common_products:
        empty_fig = px.line(title="No Common Products for Comparative Analysis")
        empty_fig.update_layout(
            plot_bgcolor=COLORS['card_bg'],
            paper_bgcolor=COLORS['card_bg'],
            font=dict(color=COLORS['text']),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        return empty_fig
    
    # Create a subplot with 3 rows
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=(
            "Warehouse vs. Transport Stock Comparison",
            "Stock Distribution by Location", 
            "Supply Chain Flow Analysis"
        ),
        vertical_spacing=0.1
    )
    
    # 1. Bar chart comparing warehouse stock vs. transport
    warehouse_totals = warehouse_df[common_products].sum()
    transport_totals = transport_df[common_products].sum()
    
    for i, product in enumerate(common_products):
        product_name = product.replace('product', 'Product ')
        fig.add_trace(
            go.Bar(
                x=[product_name], 
                y=[warehouse_totals[product]],
                name="Warehouse Stock",
                marker_color=COLORS['info'],
                legendgroup="warehouse"
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(
                x=[product_name], 
                y=[transport_totals[product]],
                name="Transport Stock",
                marker_color=COLORS['warning'],
                legendgroup="transport"
            ),
            row=1, col=1
        )
    
    # 2. Stacked area chart showing distribution across locations
    # Melt warehouse data
    warehouse_melted = warehouse_df.melt(
        id_vars=['_id'],
        value_vars=common_products,
        var_name='product',
        value_name='quantity'
    )
    warehouse_melted['location_type'] = 'Warehouse'
    warehouse_melted['location_id'] = warehouse_melted['_id']
    
    # Melt transport data
    transport_melted = transport_df.melt(
        id_vars=['_id'],
        value_vars=common_products,
        var_name='product',
        value_name='quantity'
    )
    transport_melted['location_type'] = 'Transport'
    transport_melted['location_id'] = transport_melted['_id']
    
    # Combine datasets
    combined_df = pd.concat([warehouse_melted, transport_melted])
    combined_df['product'] = combined_df['product'].str.replace('product', 'Product ')
    
    # Create a treemap
    for product in combined_df['product'].unique():
        product_df = combined_df[combined_df['product'] == product]
        warehouse_qty = product_df[product_df['location_type'] == 'Warehouse']['quantity'].sum()
        transport_qty = product_df[product_df['location_type'] == 'Transport']['quantity'].sum()
        
        fig.add_trace(
            go.Bar(
                x=["Warehouse", "Transport"],
                y=[warehouse_qty, transport_qty],
                name=product,
                text=[f"{warehouse_qty:.0f}", f"{transport_qty:.0f}"],
                textposition="auto"
            ),
            row=2, col=1
        )
    
    # 3. Line chart showing mock supply chain flow over time (simulated data)
    time_periods = ["Week 1", "Week 2", "Week 3", "Week 4"]
    
    # Simulate flow data
    np.random.seed(42)  # For reproducibility
    warehouse_flow = [np.sum(warehouse_totals) * (1 - 0.1 * i + np.random.uniform(-0.05, 0.05)) for i in range(4)]
    transport_flow = [np.sum(transport_totals) * (0.7 + 0.1 * i + np.random.uniform(-0.05, 0.05)) for i in range(4)]
    
    fig.add_trace(
        go.Scatter(
            x=time_periods,
            y=warehouse_flow,
            mode='lines+markers',
            name='Warehouse Inventory',
            line=dict(color=COLORS['info'], width=3),
            marker=dict(size=10),
            legendgroup="warehouse"
        ),
        row=3, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=time_periods,
            y=transport_flow,
            mode='lines+markers',
            name='Transport Volume',
            line=dict(color=COLORS['warning'], width=3),
            marker=dict(size=10),
            legendgroup="transport"
        ),
        row=3, col=1
    )
    
    # Update layout with consistent styling
    fig.update_layout(
        barmode='group',
        height=800,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        plot_bgcolor=COLORS['card_bg'],
        paper_bgcolor=COLORS['card_bg'],
        font=dict(color=COLORS['text']),
        margin=dict(l=40, r=40, t=100, b=40),
        hovermode="closest"
    )
    
    # Update axes
    fig.update_xaxes(showgrid=False, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.1)')
    
    return fig

# Callback to toggle navbar
@app.callback(
    Output("navbar-collapse", "is_open"),
    [Input("navbar-toggler", "n_clicks")],
    [State("navbar-collapse", "is_open")],
)
def toggle_navbar_collapse(n, is_open):
    if n:
        return not is_open
    return is_open
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True) 
