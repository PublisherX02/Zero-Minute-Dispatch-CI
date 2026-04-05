import streamlit as st
import folium
from streamlit_folium import st_folium

m = folium.Map(location=[36.8, 10.18], zoom_start=10, tiles='cartodbdark_matter', attr='CartoDB')
st_folium(m, height=400, width=700)