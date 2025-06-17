"""
This module holds the sidebar ui page for the application.
"""
import streamlit
import logging

# Custom imports
from cls.accesscontrol import AccessControl


# Set up logging
log = logging.getLogger(__name__)


def navbar(database=None) -> int:
    """
    Renders a navigation bar in the Streamlit sidebar and manages user navigation
    through the application. The navbar adjusts dynamically based on the user's
    access role and client assignments. It initializes the page state, displays
    buttons for navigation, shows user-related information, and provides a logout
    functionality.

    :param database: Optional instance of the database used for user session management.
    :type database: cls.database.Database or None
    :return: The current page index as an integer.
    :rtype: int
    """
    access_role = streamlit.session_state['user_role']
    user_id = streamlit.session_state.get('user_id')

    # Initialize the page number if it does not exist
    if not 'page' in streamlit.session_state:
        if access_role in ['auditor', 'inspector']:
            # Check if the user has any assigned cases
            accessible_clients = AccessControl.get_accessible_clients(user_id, access_role)
            if accessible_clients:
                # Set the default page for auditor and inspector to the active cases page
                page = 1
            else:
                # If no cases assigned, show home page
                page = 0
        else:
            page = 0
    else:
        page = streamlit.session_state['page']

    # Set the sidebar to st for easier access and to make sure everything happens
    # inside the sidebar unless explicitly stated
    st = streamlit.sidebar

    # Description
    st.title('Navigation')
    st.write('Please select an option from the list below.')

    # Buttons
    if st.button('Home'):
        log.debug('Home button clicked')
        page = 0

    # Show Active Cases for all users
    if st.button('Active Cases'):
        log.debug('Active cases button clicked')
        page = 1

    # Show Settings only if user has access
    if AccessControl.can_access_feature(access_role, 'settings'):
        if st.button('Settings'):
            log.debug('Settings button clicked')
            page = 2

    # About page is available to all
    if st.button('About'):
        log.debug('About button clicked')
        page = 3

    # Add a separator before user info and logout
    st.markdown("---")

    # Show user information
    st.markdown("### User Info")
    st.write(f"**User:** {streamlit.session_state.get('username', 'Unknown')}")
    st.write(f"**Role:** {access_role.title()}")

    # Show number of assigned clients for non-admin users
    if access_role != 'admin':
        accessible_clients = AccessControl.get_accessible_clients(user_id, access_role)
        st.write(f"**Assigned Clients:** {len(accessible_clients)}")

    # Add a separator before the logout button
    st.markdown("---")

    # Add logout button
    if st.button('Logout'):
        log.debug('Logout button clicked')

        # Import here to avoid circular imports
        from workflow.security import logout
        from cls.database import Database

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
        streamlit.session_state['username'] = None

        # Force reload to show login page
        streamlit.rerun()

    return page
