"""
Theme switcher component for Genoverband Streamlit application.
Allows users to toggle between light and dark themes.
"""
import streamlit as st
import os


def load_theme_css(theme_name='light'):
    """
    Load the appropriate CSS theme file based on the selected theme.
    
    :param theme_name: Name of the theme to load ('light' or 'dark')
    :return: CSS content as string
    """
    if theme_name == 'dark':
        css_file = 'src/ui/genoverband_theme_dark.css'
    else:
        css_file = 'src/ui/genoverband_theme.css'
    
    if os.path.exists(css_file):
        with open(css_file, 'r') as f:
            return f.read()
    return ""


def theme_switcher():
    """
    Create a theme switcher widget in the Streamlit sidebar.
    Manages theme state and returns the selected theme.
    
    :return: Selected theme name ('light' or 'dark')
    """
    # Initialize theme in session state if not present
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    
    # Create theme switcher in sidebar
    with st.sidebar:
        st.markdown("### 🎨 Theme")
        
        # Create columns for the toggle
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Theme toggle button with icon
            if st.session_state.theme == 'light':
                if st.button("🌙", help="Switch to dark mode", key="theme_toggle"):
                    st.session_state.theme = 'dark'
                    st.rerun()
            else:
                if st.button("☀️", help="Switch to light mode", key="theme_toggle"):
                    st.session_state.theme = 'light'
                    st.rerun()
        
        with col2:
            # Display current theme
            theme_text = "Light Mode" if st.session_state.theme == 'light' else "Dark Mode"
            st.markdown(f"**{theme_text}**")
        
        st.markdown("---")
    
    return st.session_state.theme


def apply_theme():
    """
    Apply the currently selected theme to the Streamlit app.
    This should be called in the main app after theme_switcher().
    """
    theme = st.session_state.get('theme', 'light')
    css_content = load_theme_css(theme)
    
    if css_content:
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)
    
    # Add theme-specific class to body for additional styling control
    theme_class_script = f"""
    <script>
        document.body.className = 'genoverband-theme-{theme}';
    </script>
    """
    st.markdown(theme_class_script, unsafe_allow_html=True)


def compact_theme_toggle():
    """
    Create a compact theme toggle button that can be placed anywhere.
    Returns True if theme was changed, False otherwise.
    
    :return: Boolean indicating if theme was changed
    """
    if 'theme' not in st.session_state:
        st.session_state.theme = 'light'
    
    # Create a compact toggle button
    current_theme = st.session_state.theme
    icon = "🌙" if current_theme == 'light' else "☀️"
    label = "Dark" if current_theme == 'light' else "Light"
    
    if st.button(f"{icon} {label}", key="compact_theme_toggle", help=f"Switch to {label.lower()} mode"):
        st.session_state.theme = 'dark' if current_theme == 'light' else 'light'
        return True
    
    return False