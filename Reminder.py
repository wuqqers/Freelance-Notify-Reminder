import os
import time
import tkinter as tk
from infi.systray import SysTrayIcon
import pygame
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
        self.options = Options()
        self.music_start_time = None
        self.notification_sound = None
        self.options.headless = True
        self.driver = None
        self.create_driver()  # WebDriver başlatma
        root.bind("<Unmap>", self.minimize_to_tray)
        root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray) 
        self.create_system_tray_icon()

    def create_driver(self):
        if self.driver is not None:
            try:
                self.driver.quit()
            except:
                pass
        self.driver = webdriver.Firefox(options=self.options)
        self.driver.set_window_size(1, 1)

    def create_system_tray_icon(self):
        if not BionlukApp.icon_created:
            menu_options = (("Show/Maximize", None, self.show_maximize_window),)
            self.icon = SysTrayIcon("icon.ico", "Bionluk Mesaj Bildirimi", menu_options, on_quit=self.on_quit)
            self.icon.start()
            BionlukApp.icon_created = True

    def on_quit(self, systray=None):
        pygame.mixer.quit()
        self.driver.quit()
        self.root.quit()  # Tkinter penceresini kapat
        self.icon.visible = False  # SysTrayIcon'ı gizle
        os._exit(0)

    def show_maximize_window(self, systray=None):
        self.icon.visible = False  # Simgeyi gizle
        self.root.deiconify()  # Pencereyi görünür yap
        self.root.geometry("500x100")  # Pencere boyutunu ayarla

    def minimize_to_tray(self, event=None):
        self.icon.visible = False
        self.root.withdraw()  # Pencereyi gizle

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
                if self.driver.find_elements(By.CSS_SELECTOR, "span.button-badge.unread_message_count") and \
                        self.driver.find_elements(By.CSS_SELECTOR, "span.button-badge.unread_message_count")[0].text.strip():
                    self.play_notification_sound()

    def start_app(self):
        self.driver.get("https://bionluk.com/login")

        message = "Giriş Yapılıyor..."
        self.message_label.config(text=message)
        username_input = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='E-posta veya kullanıcı adı']"))
        )
        password_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder='Şifre']")
        login_button = self.driver.find_element(By.CSS_SELECTOR, "button.super-button-green")

        username = os.getenv("BIONLUK_USERNAME")
        password = os.getenv("BIONLUK_PASSWORD")

        username_input.send_keys(username)
        password_input.send_keys(password)
        login_button.click()

        message = "Giriş Yapıldı, Mesajlar Kontrol Ediliyor"
        self.message_label.config(text=message)

        self.check_messages()

    def check_messages(self):
        try:
            unread_message_count = self.driver.find_elements(By.CSS_SELECTOR, "span.button-badge.unread_message_count")

            if unread_message_count:
                message = "Yeni mesajlar var!"
                self.play_notification_sound()
            else:
                message = "Yeni mesaj yok."
                self.stop_notification_sound()

            self.message_label.config(text=message)

            if unread_message_count and unread_message_count[0].text.strip():
                self.root.after(2000, self.check_messages)
            else:
                self.root.after(2000, self.check_messages)

            # Sayfanın yenilenmesi gerekip gerekmediğini kontrol et
            if self.check_if_page_needs_refresh():
                self.refresh_page()

        except:
            self.create_driver()  # Tarayıcı kapatılmışsa yeniden başlat
            self.start_app()

    def check_if_page_needs_refresh(self):
        # Belirli bir div'in varlığını kontrol et
        warning_div = self.driver.find_elements(By.CSS_SELECTOR, "div.version-warning")
        return len(warning_div) > 0

    def refresh_page(self):
        # Sayfayı yenile
        self.driver.refresh()

    def run(self):
        self.root.after(2000, self.start_app)
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = BionlukApp(root)
    app.run()
