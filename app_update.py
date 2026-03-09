import streamlit as st
import requests
import json
from typing import List, Tuple, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"  # Change this to your FastAPI server URL

def call_api(endpoint: str, method: str = "GET", data: dict = None) -> dict:
    """Make API calls to the FastAPI backend"""
    url = f"{API_BASE_URL}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

def show_map(coords: List[Tuple[float, float]], order: Optional[List[int]] = None):
    """Display interactive map with markers and route"""
    if not coords:
        st.info("Map will be displayed here after you add addresses.")
        return
    
    markers_js = ""
    for i, (lat, lng) in enumerate(coords):
        # Add numbered markers
        markers_js += f"""
        L.marker([{lat}, {lng}])
            .addTo(map)
            .bindPopup('Stop {i + 1}');
        """

    # Draw polyline for optimized route if order is provided
    polyline_js = ""
    if order and len(order) > 1:
        route_coords = [f"[{coords[i][0]}, {coords[i][1]}]" for i in order]
        polyline_js = f"""
        L.polyline([{', '.join(route_coords)}], {{
            color: 'red', 
            weight: 4, 
            opacity: 0.7
        }}).addTo(map);
        """

    # Calculate map center
    center_lat = sum(coord[0] for coord in coords) / len(coords)
    center_lng = sum(coord[1] for coord in coords) / len(coords)

    map_html = f"""
    <div id="map" style="height: 500px; border-radius: 10px;"></div>
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
    <script>
    var map = L.map('map').setView([{center_lat}, {center_lng}], 12);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        attribution: '© OpenStreetMap contributors'
    }}).addTo(map);
    {markers_js}
    {polyline_js}
    
    // Fit map to show all markers
    if ({len(coords)} > 1) {{
        var group = new L.featureGroup([
            {', '.join([f"L.marker([{lat}, {lng}])" for lat, lng in coords])}
        ]);
        map.fitBounds(group.getBounds().pad(0.1));
    }}
    </script>
    """
    
    st.components.v1.html(map_html, height=500)

def main():
    st.set_page_config(
        page_title="Smart Route",
        page_icon="🚚",
        layout="wide"
    )
    
    st.title("🚚 Smart Route Prototype")
    st.markdown("---")
    
    # Sidebar for adding addresses
    with st.sidebar:
        st.header("📍 Enter Addresses")
        
        # Address input
        address = st.text_input("Enter address", placeholder="e.g., 123 Main St, City, State")
        
        # Initialize session state
        if 'addresses' not in st.session_state:
            st.session_state['addresses'] = []
        if 'route_data' not in st.session_state:
            st.session_state['route_data'] = None
        
        # Add address button
        if st.button("➕ Add Address", type="primary"):
            if address.strip():
                st.session_state['addresses'].append(address.strip())
                st.session_state['route_data'] = None  # Reset route data
                st.rerun()
            else:
                st.warning("Please enter a valid address")
        
        # Display current addresses
        if st.session_state['addresses']:
            st.subheader("Current Addresses:")
            for i, addr in enumerate(st.session_state['addresses'], 1):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"{i}. {addr}")
                with col2:
                    if st.button("🗑️", key=f"delete_{i}", help="Delete address"):
                        st.session_state['addresses'].pop(i-1)
                        st.session_state['route_data'] = None
                        st.rerun()
        
        # Clear all button
        if st.session_state['addresses']:
            if st.button("🗑️ Clear All", type="secondary"):
                st.session_state['addresses'] = []
                st.session_state['route_data'] = None
                st.rerun()
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🗺️ Route Map")
        
        # Optimize route button
        if len(st.session_state['addresses']) >= 2:
            if st.button("🚀 Optimize Route", type="primary", use_container_width=True):
                with st.spinner("Optimizing route..."):
                    # Call the API to optimize route
                    response = call_api(
                        "/optimize-route", 
                        method="POST", 
                        data={"addresses": st.session_state['addresses']}
                    )
                    
                    if response:
                        st.session_state['route_data'] = response
                        st.success("Route optimized successfully!")
                    else:
                        st.error("Failed to optimize route. Please try again.")
        
        # Display map
        if st.session_state['route_data']:
            coords = st.session_state['route_data']['coordinates']
            order = st.session_state['route_data']['optimized_order']
            show_map(coords, order)
        else:
            show_map([])
    
    with col2:
        st.header("📋 Route Details")
        
        if st.session_state['route_data']:
            route_data = st.session_state['route_data']
            
            # Display metrics
            st.metric("Total Distance", f"{route_data['total_distance_km']} km")
            st.metric("Number of Stops", len(route_data['original_addresses']))
            
            # Display optimized order
            st.subheader("🎯 Optimized Order:")
            for i, addr in enumerate(route_data['optimized_addresses'], 1):
                st.write(f"{i}. {addr}")
            
            # Get directions button
            if st.button("🧭 Get Directions", use_container_width=True):
                with st.spinner("Getting directions..."):
                    directions_response = call_api(
                        "/get-directions",
                        method="POST",
                        data={"addresses": st.session_state['addresses']}
                    )
                    
                    if directions_response:
                        st.session_state['directions'] = directions_response['directions']
                        st.success("Directions loaded!")
        
        elif len(st.session_state['addresses']) >= 2:
            st.info("Click 'Optimize Route' to see route details.")
        else:
            st.info("Add at least 2 addresses to optimize the route.")
    
    # Directions section
    if 'directions' in st.session_state and st.session_state['directions']:
        st.markdown("---")
        st.header("🧭 Step-by-Step Directions")
        
        with st.expander("View Directions", expanded=True):
            for i, step in enumerate(st.session_state['directions'], 1):
                st.write(f"**{i}.** {step}")
    
    # API Status
    with st.expander("🔧 API Status"):
        if st.button("Check API Status"):
            health_response = call_api("/health")
            if health_response:
                st.success(f"✅ {health_response['message']}")
            else:
                st.error("❌ API is not responding")

if __name__ == "__main__":
    main()