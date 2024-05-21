import os
import time
import tkinter as tk
from infi.systray import SysTrayIcon
import pygame
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()  # .env dosyasını yükle

class BionlukApp:
    icon_created = False

    def __init__(self, root):
        self.root = root
        root.title("Bionluk Mesaj Bildirimi")
        root.geometry("500x100")
        root.iconbitmap('icon.ico')
        self.message_label = tk.Label(root, text="Başlatılıyor...", font=("Arial", 14))
        self.message_label.place(relx=0.5, rely=0.5, anchor="center")
        self.music_start_time = None
        self.notification_sound = None
        self.browser = None
        self.page = None
        root.bind("<Unmap>", self.minimize_to_tray)
        root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.create_system_tray_icon()

    def create_system_tray_icon(self):
        if not BionlukApp.icon_created:
            menu_options = (("Show/Maximize", None, self.show_maximize_window),)
            self.icon = SysTrayIcon("icon.ico", "Bionluk Mesaj Bildirimi", menu_options, on_quit=self.on_quit)
            self.icon.start()
            BionlukApp.icon_created = True

    def on_quit(self, systray=None):
      if self.page:
        self.page.close()
      if self.browser:
        self.browser.close()
      if self.playwright:
        self.playwright.stop()
        pygame.mixer.quit()
        self.root.quit()
        self.icon.visible = False
        os._exit(0)

    def show_maximize_window(self, systray=None):
        self.icon.visible = False
        self.root.deiconify()
        self.root.geometry("500x100")

    def minimize_to_tray(self, event=None):
        self.icon.visible = False
        self.root.withdraw()

    def play_notification_sound(self):
        if self.notification_sound and self.notification_sound.get_num_channels() > 0:
            return

        pygame.mixer.init()
        self.notification_sound = pygame.mixer.Sound("bildirim.mp3")
        self.notification_sound.play()
        self.music_start_time = time.time()
        self.check_music_status()

    def stop_notification_sound(self):
        if self.notification_sound and self.notification_sound.get_num_channels() > 0:
            self.notification_sound.stop()

    def check_music_status(self):
        if self.notification_sound is None or self.notification_sound.get_num_channels() == 0:
            return
        else:
            music_length = self.notification_sound.get_length()
            remaining_time = self.music_start_time + music_length - time.time()
            if remaining_time > 0:
                self.root.after(int(remaining_time * 1000), self.check_music_status)
            else:
                if self.check_unread_messages():
                    self.play_notification_sound()

    def start_app(self):
        self.message_label.config(text="Giriş Yapılıyor...")
        self.login()

    def login(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.firefox.launch(headless=True)
        self.page = self.browser.new_page()
        self.page.goto("https://bionluk.com/login")

        username = os.getenv("BIONLUK_USERNAME")
        password = os.getenv("BIONLUK_PASSWORD")

        self.page.fill("input[placeholder='E-posta veya kullanıcı adı']", username)
        self.page.fill("input[placeholder='Şifre']", password)
        self.page.click("button.super-button-green")

        # Yeni cihaz giriş uyarısı kontrolü
        time.sleep(5)  # Sayfanın yüklenmesi için bekleyin
        error_message_div = self.page.query_selector("div.toasted.toasted-error.outline.default")
        if error_message_div:
            error_message_text = error_message_div.inner_text()
            if "Yeni cihaz girişinizi doğrulayın." in error_message_text:
                self.message_label.config(text=error_message_text)
                self.root.after(60000, self.start_app)  # 1 dakika sonra tekrar giriş yapmayı dene
                return  # Uyarı mesajı varsa giriş kontrolünü durdur ve bekle

        self.message_label.config(text="Giriş Yapıldı, Mesajlar Kontrol Ediliyor")
        self.check_messages()

    def check_messages(self):
        unread_message_count = self.page.query_selector("span.button-badge.unread_message_count")
        
        if unread_message_count and unread_message_count.inner_text().strip():
            self.message_label.config(text="Yeni mesajlar var!")
            self.play_notification_sound()
        else:
            self.message_label.config(text="Yeni mesaj yok.")
            self.stop_notification_sound()
        
        self.root.after(2000, self.check_messages)

        if self.check_if_page_needs_refresh():
            self.refresh_page()

    def check_if_page_needs_refresh(self):
        warning_div = self.page.query_selector("div.version-warning")
        return warning_div is not None

    def refresh_page(self):
        self.page.reload()

    def run(self):
        self.root.after(2000, self.start_app)
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = BionlukApp(root)
    app.run()
