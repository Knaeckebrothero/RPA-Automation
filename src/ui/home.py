"""
This module holds the main ui page for the application.
"""
import streamlit as st


def home():
    """
    This function holds the main ui page for the application.
    """
    st.title('eBonFetcher')
    st.write('Welcome to the eBonFetcher application.')
    st.write('This application is designed to fetch your eBons from your email inbox.')
    st.write('Please select the appropriate option from the sidebar to get started.')

    st.sidebar.title('Options')
    st.sidebar.write('Please select an option from the list below.')

    st.sidebar.button('Fetch eBons')

    st.sidebar.button('Settings')

    st.sidebar.button('About')

    st.sidebar.button('Exit')
