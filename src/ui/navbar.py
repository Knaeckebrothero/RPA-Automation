"""
This module holds the sidebar ui page for the application.
"""
import streamlit
import logging

# Custom imports
#from workflow.security import logout
#from cls.database import Database


# Set up logging
log = logging.getLogger(__name__)


def navbar() -> int:
    """
    This is the sidebar ui page for the application.

    :return: The selected page number.
    """
    if not 'page' in streamlit.session_state:
        # Initialize the page number if it does not exist
        page = 0
    else:
        page = streamlit.session_state['page']

    access_role = streamlit.session_state['user_role']

    # Set the sidebar to st for easier access and to make sure everything happens
    # inside the sidebar unless explicitly stated
    st = streamlit.sidebar

    # Description
    st.title('Navigation')
    st.write('Please select an option from the list below.')

    # Buttons
    if st.button('Home'):
        log.debug('Fetch Documents button clicked')
        page = 0

    if st.button('Active Cases'):
        log.debug('Active cases button clicked')
        page = 1

    if access_role == 'admin':
        if st.button('Settings'):
            log.debug('Settings button clicked')
            page = 2

    if st.button('About'):
        log.debug('About button clicked')
        page = 3

    # Add a separator before the logout button
    st.markdown("---")

    # Add logout button
    if st.button('Logout'):
        log.debug('Logout button clicked')

        # Import here to avoid circular imports
        from workflow.security import logout
        from cls.database import Database

        db = Database.get_instance()
        logout(streamlit.session_state['session_key'], db)

        # Clear session state
        streamlit.session_state['session_key'] = None
        streamlit.session_state['user_id'] = None
        streamlit.session_state['user_role'] = None

        # Force reload to show login page
        streamlit.rerun()

    return page
