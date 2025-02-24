"""
This module holds the contents for each expander used by the active_cases page.
"""
import streamlit as st


def _icon(icon: bool = False) -> str:
    """
    This function returns the icon for the expander.
    Icons can be found here: https://streamlit-emoji-shortcodes-streamlit-app-gwckff.streamlit.app/

    :param icon: A boolean indicating if the icon should be displayed.
    :return: The icon in a string.
    """
    if icon:
        return "✅"
    else:
        return "❌"


# Step 1: Documents received
def step_1():
    with st.expander("Documents received", icon=_icon()):
        st.write("Inside the expander.")


# Step 2: Data verified
def step_2():
    with st.expander("Data verified", icon=_icon()):
        st.write("Inside the expander.")


# Step 3: Certificate issued
def step_3():
    with st.expander("Certificate issued", icon=_icon()):
        st.write("Inside the expander.")


# Step 3: Process completed
def step_4():
    with st.expander("Process completed", icon=_icon()):
        st.write("Inside the expander.")
