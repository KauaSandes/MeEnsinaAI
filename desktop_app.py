import customtkinter as ctk
from tkinter import messagebox, Text
from PIL import Image, ImageTk  # Adicionado para manipular imagens
import threading
from auth import init_db, register_user, authenticate_user
from gameplay_analyzer import run_gameplay_analysis, get_reports_csv

# Mapeamento de jogos para executáveis
GAME_EXECUTABLES = {
    "Counter-Strike 2": "cs2.exe",
    "Street Fighter 5": "StreetFighter5.exe"
}

class GameAnalysisApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.iconbitmap("Logo (1)MeEnsinaAI - FUNDO - PNG.ico")
        self.title("MeEnsina-AI")
        self.geometry("1920x1080")
        ctk.set_appearance_mode("dark")  # Fundo preto
        ctk.set_default_color_theme("dark-blue")  # Usaremos vermelho manualmente nos elementos
        self.logo_img = ctk.CTkImage(Image.open("Logo (1)MeEnsinaAI - FUNDO - PNG.ico"), size=(120, 120))
        self.user_email = None
        self.current_game = None
        self.game_exe = None
        self.is_recording = False
        init_db()
        self.configure(fg_color="#18181A")
        self.modern_font = ctk.CTkFont(family="Segoe UI", size=16)
        self.show_auth_screen()

    def clear_frame(self):
        for widget in self.winfo_children():
            widget.destroy()

    def show_auth_screen(self):
        self.clear_frame()
        self.title("Login / Cadastro")
        self.configure(fg_color="#18181A")
        # LOGO
        logo_label = ctk.CTkLabel(self, image=self.logo_img, text="", fg_color="#18181A")
        logo_label.pack(pady=(30, 10))
        # ONBOARDING
        onboarding_text = (
            "Transforme sua Gameplay\n"
            "Simples para você, poderoso para seu jogo\n\n"
            "01\nGrave sua Partida\n"
            "Nosso aplicativo opera discretamente em segundo plano, capturando sua tela enquanto você joga, sem atrapalhar sua performance.\n\n"
            "02\nAnálise por Inteligência Artificial\n"
            "Após a partida, nossa IA processa os dados, identifica seus padrões, acertos e, mais importante, os pontos que precisam de melhoria.\n\n"
            "03\nReceba Dicas e Treinos Personalizados\n"
            "Você recebe um relatório completo com feedback específico e uma rotina de treinos para aprimorar suas habilidades de forma focada e eficiente."
        )
        onboarding_label = ctk.CTkLabel(self, text=onboarding_text, font=self.modern_font, justify="left", text_color="#FF2D2D", fg_color="#18181A")
        onboarding_label.pack(pady=(0, 10), padx=30)
        tabview = ctk.CTkTabview(self, width=400, fg_color="#18181A")
        tabview.pack(pady=10, padx=60, fill="both", expand=True)
        tabview.add("Login")
        tabview.add("Criar Conta")
        # Aba de Login
        login_frame = tabview.tab("Login")
        email_entry = ctk.CTkEntry(login_frame, placeholder_text="Email", width=300)
        email_entry.pack(pady=12, padx=10)
        password_entry = ctk.CTkEntry(login_frame, placeholder_text="Senha", show="*", width=300)
        password_entry.pack(pady=12, padx=10)
        login_button = ctk.CTkButton(login_frame, text="Entrar", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=lambda: self.login(email_entry.get(), password_entry.get()))
        login_button.pack(pady=12, padx=10)
        # Aba de Cadastro
        signup_frame = tabview.tab("Criar Conta")
        new_email_entry = ctk.CTkEntry(signup_frame, placeholder_text="Email de cadastro", width=300)
        new_email_entry.pack(pady=12, padx=10)
        new_password_entry = ctk.CTkEntry(signup_frame, placeholder_text="Senha", show="*", width=300)
        new_password_entry.pack(pady=12, padx=10)
        confirm_password_entry = ctk.CTkEntry(signup_frame, placeholder_text="Confirme a senha", show="*", width=300)
        confirm_password_entry.pack(pady=12, padx=10)
        signup_button = ctk.CTkButton(signup_frame, text="Cadastrar", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=lambda: self.signup(new_email_entry.get(), new_password_entry.get(), confirm_password_entry.get()))
        signup_button.pack(pady=12, padx=10)

    def login(self, email, password):
        if authenticate_user(email, password):
            self.user_email = email
            self.show_game_selection()
        else:
            messagebox.showwarning("Falha no Login", "Email ou senha inválidos.")

    def signup(self, email, password, confirm_password):
        if not email or not password:
            messagebox.showwarning("Cadastro", "Preencha todos os campos.")
        elif password != confirm_password:
            messagebox.showwarning("Cadastro", "As senhas não coincidem.")
        else:
            if register_user(email, password):
                messagebox.showinfo("Sucesso", "Conta criada! Faça o login para continuar.")
                self.show_auth_screen()
            else:
                messagebox.showerror("Erro", "Já existe uma conta com este email.")

    def show_game_selection(self):
        self.clear_frame()
        self.title("Seleção de Jogo")
        self.configure(fg_color="#18181A")
        label = ctk.CTkLabel(self, text=f"Bem-vindo, {self.user_email}!\nEscolha um jogo para analisar:", font=self.modern_font, text_color="white", fg_color="#18181A")
        label.pack(pady=20)
        cs_button = ctk.CTkButton(self, text="Counter-Strike 2", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=lambda: self.select_game("Counter-Strike 2"), height=50)
        cs_button.pack(pady=10, padx=20, fill="x")
        sf_button = ctk.CTkButton(self, text="Street Fighter 5", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=lambda: self.select_game("Street Fighter 5"), height=50)
        sf_button.pack(pady=10, padx=20, fill="x")
        history_button = ctk.CTkButton(self, text="Ver Histórico de Análises", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=self.show_history, height=40)
        history_button.pack(pady=20, padx=20, fill="x")

    def select_game(self, game_name):
        self.current_game = game_name
        self.game_exe = GAME_EXECUTABLES[game_name]
        self.show_analysis_screen()
        
    def show_history(self):
        self.clear_frame()
        self.title("Histórico de Análises")
        self.configure(fg_color="#18181A")
        back_button = ctk.CTkButton(self, text="Voltar", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=self.show_game_selection)
        back_button.pack(pady=10, anchor="w", padx=10)
        csv_content = get_reports_csv()
        text_area = Text(self, wrap='word', bg="#18181A", fg="white", insertbackground="white")
        if csv_content:
            text_area.insert('1.0', csv_content)
        else:
            text_area.insert('1.0', "Nenhum relatório de análise disponível.")
        text_area.pack(pady=10, padx=10, fill="both", expand=True)

    def show_analysis_screen(self):
        self.clear_frame()
        self.title(f"Análise - {self.current_game}")
        self.configure(fg_color="#18181A")
        label = ctk.CTkLabel(self, text=f"Jogo: {self.current_game}\nExecutável: {self.game_exe}", font=self.modern_font, text_color="white", fg_color="#18181A")
        label.pack(pady=10)
        instructions = """
        Instruções:
        1. Abra o jogo em tela cheia.
        2. Certifique-se de que a janela do jogo está visível.
        3. Clique no botão 'Começar Gravação' para iniciar.
        """
        instruction_label = ctk.CTkLabel(self, text=instructions, justify="left", text_color="#FF2D2D", font=self.modern_font, fg_color="#18181A")
        instruction_label.pack(pady=10)
        self.record_button = ctk.CTkButton(self, text="Começar Gravação", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=self.toggle_recording, height=40)
        self.record_button.pack(pady=20)
        self.status_label = ctk.CTkLabel(self, text="", font=self.modern_font, text_color="white", fg_color="#18181A")
        self.status_label.pack(pady=10)
        back_button = ctk.CTkButton(self, text="Escolher outro jogo", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=self.show_game_selection)
        back_button.pack(pady=10)
        
    def toggle_recording(self):
        if not self.is_recording:
            self.is_recording = True
            self.record_button.configure(text="Interromper Gravação", state="normal")
            self.status_label.configure(text="Gravando gameplay...")
            
            # Executa a análise em uma thread separada para não travar a UI
            self.analysis_thread = threading.Thread(target=self.run_analysis_thread)
            self.analysis_thread.start()
        else:
            messagebox.showinfo("Gravação", "A gravação será interrompida ao final da análise.")
            self.record_button.configure(state="disabled")

    def run_analysis_thread(self):
        result = run_gameplay_analysis(self.game_exe, self.current_game)
        self.is_recording = False
        
        if result and result.get('success'):
            self.show_results_screen(result['report'])
        else:
            messagebox.showerror("Erro na Análise", result.get('message', 'Ocorreu um erro desconhecido.'))
            self.show_game_selection()

    def show_results_screen(self, report):
        self.clear_frame()
        self.title("Relatório de Análise")
        self.configure(fg_color="#18181A")
        report_text = Text(self, wrap='word', height=25, width=80, bg="#18181A", fg="white", insertbackground="white")
        report_text.insert('1.0', report)
        report_text.pack(pady=10, padx=10, fill="both", expand=True)
        button_frame = ctk.CTkFrame(self, fg_color="#18181A")
        button_frame.pack(pady=10)
        new_analysis_button = ctk.CTkButton(button_frame, text="Nova Análise (Mesmo Jogo)", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=self.show_analysis_screen)
        new_analysis_button.pack(side="left", padx=10)
        change_game_button = ctk.CTkButton(button_frame, text="Escolher Outro Jogo", fg_color="#FF2D2D", hover_color="#B22222", text_color="white", font=self.modern_font, corner_radius=20, command=self.show_game_selection)
        change_game_button.pack(side="left", padx=10)


if __name__ == "__main__":
    app = GameAnalysisApp()
    app.mainloop()