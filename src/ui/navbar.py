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


def navbar(database=None) -> int:
    """
    This is the sidebar ui page for the application.

    :return: The selected page number.
    """
    access_role = streamlit.session_state['user_role']

    # Initialize the page number if it does not exist
    if not 'page' in streamlit.session_state:
        if access_role in ['auditor', 'inspector']:
            # Set the default page for auditor and inspector to the active cases page
            page = 1
        else:
            page = 0
    else:
        page = streamlit.session_state['page']
        # TODO: Add logic to prevent the users from accessing the pages they are not allowed to

    # Set the sidebar to st for easier access and to make sure everything happens
    # inside the sidebar unless explicitly stated
    st = streamlit.sidebar

    # Description
    st.title('Navigation')
    st.write('Please select an option from the list below.')

    # Buttons
    #if access_role == 'admin':  # TODO: Move the logic to process mails to another place or restrict it to the admin
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

    # TODO: Move log display to another page or restrict it to only be visible to the admin
    # if access_role in ['admin', 'inspector']:
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
        # TODO: Why is this necessary?

        # Check if the database instance is provided, otherwise fetch the instance
        if database:
            db = database
        else:
            db = Database().get_instance()

        logout(streamlit.session_state['session_key'], db)

        # Clear session state
        streamlit.session_state['session_key'] = None
        streamlit.session_state['user_id'] = None
        streamlit.session_state['user_role'] = None

        # Force reload to show login page
        streamlit.rerun()

    return page
