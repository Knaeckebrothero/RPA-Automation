# German Translation Implementation Plan

## Overview
This document outlines the plan for implementing German translations in the Document Fetcher application. The goal is to translate all user-facing text elements into German while maintaining the existing functionality.

## Current Status
- A comprehensive dictionary of English to German translations has been created in `src/translations.py`
- The application currently has no internationalization (i18n) or localization mechanism
- All text is hardcoded in English throughout the codebase

## Implementation Approach

### 1. Integration Method
The simplest approach is to use the `translate()` function from `translations.py` to translate text at the point of use. This involves:

1. Importing the translation function in each file that contains user-facing text:
   ```python
   from translations import translate as _
   ```

2. Wrapping all user-facing text strings with the translation function:
   ```python
   # Before
   st.header('Document Fetcher')
   
   # After
   st.header(_('Document Fetcher'))
   ```

### 2. Files to Modify
The following files need to be modified to implement translations:

- `src/main.py` - Application entry point and page configuration
- `src/ui/navbar.py` - Navigation sidebar
- `src/ui/pages.py` - Main page content
- `src/ui/expander_stages.py` - Expandable UI components
- `src/ui/visuals.py` - Visual elements and badges

### 3. Special Considerations

#### String Formatting
For strings that include variables or formatting, ensure the translation function is applied correctly:

```python
# Before
st.success(f"Successfully created {created_count} new audit cases.")

# After
st.success(_("Successfully created") + f" {created_count} " + _("new audit cases."))
```

#### HTML Content
For HTML content, ensure the translation is applied before the HTML is rendered:

```python
# Before
st.markdown(f"**Case {selected_case['case_id']} Stage:** {visuals.stage_badge(selected_case['stage'])}", unsafe_allow_html=True)

# After
st.markdown(f"**{_('Case')} {selected_case['case_id']} {_('Stage')}:** {visuals.stage_badge(selected_case['stage'])}", unsafe_allow_html=True)
```

#### Dynamic Content
For dynamically generated content (like stage badges), ensure the translation is applied at the point where the text is defined:

```python
# In visuals.py
status_map = {
    1: (_("Waiting for documents"), "#FFA500"),  # Orange
    2: (_("Data verification"), "#1E90FF"),  # Blue
    # ...
}
```

### 4. Testing Strategy
After implementing the translations:

1. Run the application and navigate through all pages
2. Verify that all user-facing text appears in German
3. Check for any untranslated text or formatting issues
4. Test all functionality to ensure it still works as expected

### 5. Future Enhancements
For a more robust internationalization solution in the future, consider:

1. Adding a language selector in the UI
2. Supporting additional languages
3. Using a more sophisticated i18n framework like Flask-Babel or gettext

## Implementation Steps

1. Add the translation import to each file
2. Modify each file to use the translation function for all user-facing text
3. Test the application to ensure all text is translated
4. Fix any issues or missing translations
5. Document the changes for future maintenance