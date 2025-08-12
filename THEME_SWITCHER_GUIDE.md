# Genoverband Theme Switcher Guide

## Overview

The application now supports both **Light** and **Dark** themes with Genoverband's brand colors. Users can switch between themes dynamically using the theme switcher in the sidebar.

## Features

### 🎨 Dual Theme Support

1. **Light Theme** (`genoverband_theme.css`)
   - Clean white backgrounds
   - Violet primary accents (#7B68EE)
   - Professional appearance for daytime use
   - High contrast for readability

2. **Dark Theme** (`genoverband_theme_dark.css`)
   - Dark navy backgrounds (#0F172A)
   - Preserved brand colors with adjusted brightness
   - Reduced eye strain for evening work
   - Elegant gradient effects

## How It Works

### Theme Switching
- A theme toggle button appears in the sidebar
- Click 🌙 to switch to dark mode
- Click ☀️ to switch to light mode
- The theme preference is stored in session state
- The page automatically refreshes with the new theme

### Technical Implementation

```python
# The theme system consists of three main components:

1. Theme Switcher Component (src/ui/theme_switcher.py)
   - Manages theme state
   - Provides UI toggle
   - Loads appropriate CSS

2. CSS Theme Files
   - genoverband_theme.css (light mode)
   - genoverband_theme_dark.css (dark mode)

3. Main Integration (src/main.py)
   - Initializes theme switcher
   - Applies selected theme on load
```

## Color Schemes

### Light Mode Colors
- **Primary**: Violet (#7B68EE)
- **Secondary**: Light Violet (#E6E0FF)
- **Accent**: Turquoise (#06B6D4)
- **Text**: Dark Blue-Gray (#2C3E50)
- **Background**: White (#FFFFFF)

### Dark Mode Colors
- **Primary**: Violet (#7B68EE)
- **Background**: Dark Navy (#0F172A)
- **Surface**: Dark Blue (#1E293B)
- **Text**: Light Gray (#F1F5F9)
- **Accent**: Turquoise (#06B6D4)

## Customization

### Modifying Themes

To customize either theme:

1. Edit the respective CSS file:
   - Light: `src/ui/genoverband_theme.css`
   - Dark: `src/ui/genoverband_theme_dark.css`

2. Update color variables in the `:root` section:
```css
:root {
    --genoverband-violet: #7B68EE;
    /* Add or modify colors here */
}
```

### Adding New Theme Variants

To add a new theme:

1. Create a new CSS file: `src/ui/genoverband_theme_[name].css`
2. Update `theme_switcher.py` to include the new theme:
```python
def load_theme_css(theme_name='light'):
    if theme_name == 'your_new_theme':
        css_file = 'src/ui/genoverband_theme_[name].css'
```

## UI Elements Styled

Both themes customize:
- ✅ Buttons (primary, secondary, hover states)
- ✅ Input fields and forms
- ✅ Sidebars and navigation
- ✅ Metrics and cards
- ✅ Tables and dataframes
- ✅ Expandable sections
- ✅ Tabs and selections
- ✅ Progress bars
- ✅ Notifications (success, warning, error)
- ✅ Charts and visualizations
- ✅ Scrollbars
- ✅ Links and headers

## Running the Application

```bash
# Start the application with theme support
streamlit run src/main.py

# The theme switcher will appear automatically in the sidebar
```

## Browser Compatibility

The themes are tested and work with:
- Chrome/Edge (Chromium-based)
- Firefox
- Safari
- Opera

## Performance Considerations

- Themes are loaded once per session
- CSS is injected inline for instant switching
- No external dependencies or fonts required
- Minimal impact on page load time

## Troubleshooting

### Theme Not Applying
1. Clear browser cache
2. Restart Streamlit server
3. Check CSS file paths are correct

### Theme Reverting on Refresh
- This is expected behavior as session state resets
- Consider implementing persistent storage (cookies/localStorage) for permanent preferences

### Custom Components Not Styled
- Add specific selectors to the theme CSS files
- Use browser DevTools to identify component classes

## Future Enhancements

Potential improvements:
1. **Auto-detect system theme** - Match OS dark/light preference
2. **Theme persistence** - Save preference across sessions
3. **Custom color picker** - Allow users to customize colors
4. **High contrast mode** - Accessibility enhancement
5. **Theme presets** - Multiple theme variations (blue, green, etc.)

## Support

For theme-related issues or customization requests:
1. Check the CSS files for the specific element
2. Use browser DevTools to inspect styling
3. Modify the appropriate theme CSS file
4. Test both themes after changes