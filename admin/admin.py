import tkinter as tk
from tkinter import ttk
import requests
import threading

API_BASE_URL = 'http://10.100.102.3:5000'
REFRESH_INTERVAL = 5  # Refresh interval in seconds

class AdminApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Admin Dashboard")
        self.geometry("300x200")
        self.resizable(False, False)

        self.dashboard_frame = ttk.Frame(self)
        
        
        self.blacklisted_users_label = ttk.Label(self.dashboard_frame, text="Blacklisted Users")
        self.blacklisted_users_label.grid(row=0, column=1, padx=10, pady=10, sticky=tk.W)
        
        self.users_label = ttk.Label(self.dashboard_frame, text="Users")
        self.users_label.grid(row=0, column=0, padx=10, pady=10, sticky=tk.W)
        
        self.files_label = ttk.Label(self.dashboard_frame, text="Files")
        self.files_label.grid(row=0, column=2, padx=10, pady=10, sticky=tk.W)
        
        self.blacklisted_users_listbox = tk.Listbox(self.dashboard_frame)
        self.blacklisted_users_listbox.grid(row=1, column=1, padx=10, pady=10, sticky=tk.NSEW)
        
        self.users_listbox = tk.Listbox(self.dashboard_frame)
        self.users_listbox.grid(row=1, column=0, padx=10, pady=10, sticky=tk.NSEW)
        
        self.files_listbox = tk.Listbox(self.dashboard_frame)
        self.files_listbox.grid(row=1, column=2, padx=10, pady=10, sticky=tk.NSEW)
        
        self.blacklist_button = ttk.Button(self.dashboard_frame, text="Blacklist User", style="Primary.TButton", command=self.blacklist_user)
        self.blacklist_button.grid(row=2, column=0, padx=10, pady=10, sticky=tk.W)

        self.server_status = ttk.Label(self.dashboard_frame, text="Server is UP",foreground='green')
        self.server_status.grid(row=2, column=1, padx=10, pady=10, sticky=tk.NSEW)

        self.columnconfigure(0, weight=1)  # Make columns expandable
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)  # Make row expandable

        self.refresh_thread = None
    
    def update_lists(self):
        try: 
            print('hello')
            self.populate_blacklisted_users()
            self.populate_users()
            self.populate_files()
            self.server_status.config(text='server is UP',foreground='green')
        except requests.exceptions.ConnectionError as e:
            print('server is downs')
            self.server_status.config(text='server is DOWN',foreground='red')
            
            self.after(REFRESH_INTERVAL * 1000, self.update_lists)  # Schedule the next update
        

    def populate_blacklisted_users(self):
        self.blacklisted_users_listbox.delete(0, tk.END)
        response = requests.get(f'{API_BASE_URL}/admin/blacklist', cookies=self.cookies)
        if response.status_code == 200:
            blacklist = response.json()
            for ip in blacklist['blacklisted']:
                self.blacklisted_users_listbox.insert(tk.END, ip)
        else:
            self.blacklisted_users_listbox.insert(tk.END, 'Failed to retrieve blacklist')
    
    def populate_users(self):
        self.users_listbox.delete(0, tk.END)
        response = requests.get(f'{API_BASE_URL}/admin/users', cookies=self.cookies)
        if response.status_code == 200:
            users = response.json()
            for user in users.values():
                print(users)
                self.users_listbox.insert(tk.END, f"{user['ip']}")
        else:
            self.users_listbox.insert(tk.END, 'Failed to retrieve users')
    
    def populate_files(self):
        self.files_listbox.delete(0, tk.END)
        response = requests.get(f'{API_BASE_URL}/scrape/all')
        if response.status_code == 200:
            files = response.json()
            for file in files:
                self.files_listbox.insert(tk.END, f"{file['name']} - Info Hash: {file['info_hash']}")
        else:
            self.files_listbox.insert(tk.END, 'Failed to retrieve files')
    
    def blacklist_user(self):
        selected_user = self.users_listbox.get(tk.ACTIVE)
        username = selected_user.strip()
        print(username)
        response = requests.post(f'{API_BASE_URL}/admin/blacklist', json=[username], cookies = self.cookies)
        print(response.json())
        if response.status_code == 200:
            self.update_lists()
    
    def start(self):
        self.dashboard_frame.pack(fill=tk.BOTH, expand=True)
        self.update_lists()
        self.mainloop()
    
    def stop(self):
        self.after_cancel(self.refresh_thread)
        self.destroy()
    
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        payload = {'username': username, 'password': password}
        try: 
            response = requests.post(f'{API_BASE_URL}/login', data=payload, headers={'Content-Type' : 'application/x-www-form-urlencoded'}, timeout=0.5)
            if response.status_code == 200:
                self.login_frame.pack_forget()
                self.cookies = response.cookies
                self.geometry("450x300")
                self.minsize(450, 300)  
                self.resizable(True,True)
                self.start()
            else:
                self.error_label.config(text='Invalid username or password')
        except (TimeoutError, requests.exceptions.ConnectTimeout): 
            self.error_label.config(text='Server is offline currently')



            
    
    def create_login_frame(self):
        self.login_frame = ttk.Frame(self)
        
        self.username_label = ttk.Label(self.login_frame, text="Username")
        self.username_label.pack(pady=10)
        
        self.username_entry = ttk.Entry(self.login_frame)
        self.username_entry.pack()
        
        self.password_label = ttk.Label(self.login_frame, text="Password")
        self.password_label.pack(pady=10)
        
        self.password_entry = ttk.Entry(self.login_frame, show='*')
        self.password_entry.pack()
        
        self.login_button = ttk.Button(self.login_frame, text="Login", style="Primary.TButton", command=self.login)
        self.login_button.pack(pady=10)
        
        self.error_label = ttk.Label(self.login_frame, text="", style="Error.TLabel")
        self.error_label.pack()
        
        self.login_frame.pack(fill=tk.BOTH, expand=True)

if __name__ == '__main__':
    app = AdminApp()
    app.create_login_frame()
    app.mainloop()
