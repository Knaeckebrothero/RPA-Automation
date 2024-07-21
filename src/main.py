"""
This file holds the main function for the application.

https://docs.streamlit.io/
"""
from dotenv import load_dotenv, find_dotenv
import streamlit as st
# Custom imports
import src.ui.home as ui
import config.startup as startup


def main():
    if 'initialized' not in st.session_state:
        load_dotenv(find_dotenv())
        startup.streamlit_session_state()
        startup.streamlit_page()

        # Mark the session as initialized
        st.session_state.initialized = True
        st.session_state.logger.info('Initialized the session')

    # Set the logger and mailbox to variables for easy access
    log = st.session_state.logger
    mailbox = st.session_state.mailbox

    # Set the page configuration and start the UI
    log.debug('Starting the UI')
    ui.home(log, mailbox)
    log.debug('UI started')

    # Log end of script execution to track streamlit reruns
    st.session_state.rerun_counter += 1
    log.debug(f'script executed {st.session_state.rerun_counter} times')
    if st.session_state.rerun_counter % 5 == 0:
        log.info(f'script executed {st.session_state.rerun_counter} times')

    for var in st.session_state:
        log.error(f'{var} = {st.session_state[var]}')


if __name__ == '__main__':
    main()
