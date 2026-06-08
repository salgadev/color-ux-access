import gradio as gr

class ColorUXAccessTheme(gr.themes.Base):
    def __init__(self):
        super().__init__(
            primary_hue="blue",
            secondary_hue="gray",
            neutral_hue="gray",
            radius_size=gr.themes.sizes.radius_sm,
            font=[gr.themes.GoogleFont("Inter"), "Arial", "sans-serif"],
        )
        # Override specific colors for better accessibility
        self.primary = "#1E88E5"  # Blue
        self.secondary = "#424242"  # Dark gray
        self.background = "#FFFFFF"  # White
        self.background_fill = "#F5F5F5"  # Light gray
        self.border_color = "#E0E0E0"  # Border gray
        self.text_color = "#212121"  # Dark text
        
        # Button styling
        self.button_primary_background_fill = "*primary"
        self.button_primary_background_fill_hover = "*primary*0.9"
        self.button_primary_text_color = "#FFFFFF"
        
        self.button_secondary_background_fill = "*secondary"
        self.button_secondary_background_fill_hover = "*secondary*0.9"
        self.button_secondary_text_color = "#FFFFFF"

# Instantiate the theme
color_ux_access_theme = ColorUXAccessTheme()