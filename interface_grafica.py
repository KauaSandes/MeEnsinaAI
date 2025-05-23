import customtkinter as ctk
import os
import re
import glob
from datetime import datetime

class GameplayTipsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MeEnsinaAI")
        self.root.geometry("700x550")  # Slightly larger for better spacing
        ctk.set_appearance_mode("dark")  # Set dark theme
        ctk.set_default_color_theme("dark-blue")  # Use dark-blue theme for modern look

        # Main frame for better organization
        self.main_frame = ctk.CTkFrame(master=root, corner_radius=10)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Title Label
        self.title_label = ctk.CTkLabel(
            master=self.main_frame,
            text="Dicas Gameplay Super Mario Bros. (NES) ",
            font=ctk.CTkFont(family="Roboto", size=20, weight="bold"),
            text_color="#E0E0E0"
        )
        self.title_label.pack(pady=(10, 20))

        # Load Button
        self.load_button = ctk.CTkButton(
            master=self.main_frame,
            text="Carregar dicas mais recentes",
            command=self.load_tips,
            font=ctk.CTkFont(family="Roboto", size=14),
            fg_color="#4CAF50",
            hover_color="#45A049",
            corner_radius=8,
            height=40
        )
        self.load_button.pack(pady=10)

        # Text Area with Scrollbar
        self.text_area = ctk.CTkTextbox(
            master=self.main_frame,
            wrap="word",
            width=600,
            height=350,
            font=ctk.CTkFont(family="Roboto", size=12),
            text_color="#E0E0E0",
            fg_color="#2B2B2B",
            border_color="#4CAF50",
            border_width=2,
            corner_radius=10,
            scrollbar_button_color="#4CAF50",
            scrollbar_button_hover_color="#45A049"
        )
        self.text_area.pack(pady=10, padx=10, fill="both", expand=True)

        # Status Label
        self.status_label = ctk.CTkLabel(
            master=self.main_frame,
            text="Nenhuma dica encontrada",
            font=ctk.CTkFont(family="Roboto", size=12),
            text_color="#B0B0B0"
        )
        self.status_label.pack(pady=10)

    def load_tips(self):
        """Load and display the latest gameplay tips file."""
        try:
            # Find the latest gameplay_tips_*.md file
            tips_files = glob.glob("gameplay_tips_*.md")
            if not tips_files:
                self.status_label.configure(text="Nenhuma dica encontrada!", text_color="#FF5252")
                self.text_area.delete("1.0", "end")
                return

            # Get the most recent file based on timestamp in filename
            latest_file = max(tips_files, key=os.path.getctime)
            self.status_label.configure(
                text=f"Loaded: {os.path.basename(latest_file)}",
                text_color="#4CAF50"
            )

            # Read and parse the Markdown file
            with open(latest_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Clear previous content
            self.text_area.delete("1.0", "end")

            # Basic Markdown parsing for headers and lists
            lines = content.splitlines()
            for line in lines:
                if line.startswith("# "):
                    self.text_area.insert("end", line[2:] + "\n", "header")
                elif line.startswith("## "):
                    self.text_area.insert("end", line[3:] + "\n", "subheader")
                elif line.startswith("- "):
                    self.text_area.insert("end", "• " + line[2:] + "\n", "list")
                else:
                    self.text_area.insert("end", line + "\n", "normal")

            # Configure text tags for styling
            self.text_area.tag_configure("header", font=ctk.CTkFont(family="Roboto", size=14, weight="bold"), foreground="#4CAF50")
            self.text_area.tag_configure("subheader", font=ctk.CTkFont(family="Roboto", size=13, weight="bold"), foreground="#66BB6A")
            self.text_area.tag_configure("list", font=ctk.CTkFont(family="Roboto", size=12), foreground="#E0E0E0")
            self.text_area.tag_configure("normal", font=ctk.CTkFont(family="Roboto", size=12), foreground="#E0E0E0")

        except Exception as e:
            self.status_label.configure(text=f"Erro ao carregar arquivo: {str(e)}", text_color="#FF5252")
            self.text_area.delete("1.0", "end")

if __name__ == "__main__":
    root = ctk.CTk()
    app = GameplayTipsGUI(root)
    root.mainloop()