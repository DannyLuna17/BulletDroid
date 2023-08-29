# Standar imports
import json
import os
import random
from queue import Queue
from threading import Thread
from urllib.parse import quote
import time

# Third party imports
import kivy
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
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
from kivy.graphics import Color, Rectangle, Line
from retry_requests import retry
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
kivy.require('2.2.0')

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
    def __init__(self, border_color=(1, 1, 1, 1), bg_color=(0, 0, 0, 0), **kwargs):
        super(BorderedButton, self).__init__(**kwargs)
        self.border_color = border_color
        self.bg_color = bg_color
        self.update_graphics()

        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            self.rect = Rectangle(pos=self.pos, size=self.size)
            Color(*self.border_color)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=dp(1))

    def on_press(self):
        super(BorderedButton, self).on_press()
        self.bg_color = (0.3, 0.3, 0.3, 1)  # Change Color on Press
        self.update_graphics()

    def on_release(self):
        super(BorderedButton, self).on_release()
        self.bg_color = (0, 0, 0, 1)  # Change Color on Release
        self.update_graphics()

class BulletApp(App):
    ICON_PATH = "src/logo.png"
    WATERMARK_PATH = "src/watermark.png"
    LOGS_TYPE = "Logs"
    HITS_TYPE = "Hits"
    DEADS_TYPE = "Deads"

    def show_full_screen(self, text):
        """Displays a fullscreen popup with the given text."""

        full_screen_layout = BoxLayout(orientation='vertical')
        full_screen_label = TextInput(text=text, readonly=True, multiline=True)
        close_button = Button(text="Close", size_hint=(1, 0.1))

        full_screen_layout.add_widget(full_screen_label)
        full_screen_layout.add_widget(close_button)

        self.full_screen_popup = Popup(title="View Content", content=full_screen_layout, size_hint=(0.9, 0.9))
        close_button.bind(on_press=self.full_screen_popup.dismiss)
        self.full_screen_popup.open()

    def build(self):
        # Initialize variables

        self.combo, self.proxies = "", ""
        self.proxy_switch_status = True
        self.variables = {}
        self.responses = {}
        self.headers = {}
        self.cookies = {}
        self.find_variables = {}
        self.progreso = 0
        self.icon = self.ICON_PATH
        self.dropdown_buttons = []

        self.layout = GridLayout(cols=1)

        self.state_label = Label(text="State: Sleeping", size_hint=(0.3, 0.1), pos_hint={'right': 1, 'bottom': 1}, halign="right", valign="bottom", font_size=dp(20))
        self.layout.add_widget(self.state_label)

        # Add Progress Bar
        self.progress_bar = ProgressBar(max=100, value=0, size_hint=(1, 0.05))
        self.layout.add_widget(self.progress_bar)

        # Spinner Configuration
        self.options_spinner = Spinner(text='Select Config', values=('Bees', "Custom"))
        
        # Threads Configuration
        threads_label = Label(text="Threads:")
        self.threads_input = TextInput(input_filter="int", multiline=False)
        threads_layout = BoxLayout(orientation='horizontal', padding=dp(10), spacing=dp(5), size_hint=(1, 0.15))
        threads_layout.add_widget(threads_label)
        threads_layout.add_widget(self.threads_input)
        threads_layout.add_widget(self.options_spinner)
        self.layout.add_widget(threads_layout)

        # Buttons Configuration
        buttons_layout = BoxLayout(orientation='horizontal', padding=dp(10), spacing=dp(5), size_hint=(1, 0.16))
        self.load_button = BorderedButton(text="Load Combo", background_color=(0, 0, 0, 1))
        self.load_button.bind(on_press=self.load_file)
        self.run_button = BorderedButton(text="Run Combo", background_color=(0, 0, 0, 1))
        self.run_button.bind(on_press=self.run_file)
        self.proxies_button = BorderedButton(text="Load Proxies", background_color=(0, 0, 0, 1))
        self.proxies_button.bind(on_press=self.load_proxies)
        self.load_instructions_button = BorderedButton(text="Load Config", background_color=(0, 0, 0, 1))
        self.load_instructions_button.bind(on_press=self.load_instructions)
        buttons_layout.add_widget(self.load_button)
        buttons_layout.add_widget(self.run_button)
        buttons_layout.add_widget(self.load_instructions_button)
        buttons_layout.add_widget(self.proxies_button)

        # Spinner for proxy selection
        self.proxy_spinner = Spinner(
            text='No Proxy',
            values=('No Proxy', 'HTTP', 'HTTPS', 'SOCKS4', 'SOCKS5')
        )
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

        def create_scrollable_label(text, color):
            label = Label(text=text, font_size=dp(15), size_hint_y=None, size_hint_x=None, halign="left", valign="top", color=color)
            label.bind(texture_size=label.setter('size'))
            scroll_view = ScrollView(do_scroll_x=True, do_scroll_y=True)
            box = BoxLayout(size_hint_y=None, size_hint_x=None, orientation='vertical')
            box.bind(minimum_height=box.setter('height'))
            box.bind(minimum_width=box.setter('width'))
            box.add_widget(label)
            scroll_view.add_widget(box)
            return scroll_view, label
        
        def create_scrollable_label_with_clear_button(text, color, info_text):
            scroll_view, label = create_scrollable_label(text, color)

            info_label = Label(text=info_text, halign="left", valign="center", color=(1, 1, 1, 1))

            box_with_buttons = BoxLayout(orientation='vertical')
            box_with_buttons.add_widget(scroll_view)

            return box_with_buttons, label, info_label
    
        self.result_logs_box, self.result_logs_label, self.result_logs_info_label = create_scrollable_label_with_clear_button("Logs:\n", (1, 1, 1, 1), info_text="CPM: 0")
        self.result_hits_box, self.result_hits_label, self.result_hits_info_label = create_scrollable_label_with_clear_button("Hits:\n", (0, 1, 0, 1), info_text="Hits: 0")
        self.result_deads_box, self.result_deads_label, self.result_deads_info_label = create_scrollable_label_with_clear_button("Deads:\n", (1, 0, 0, 1), info_text="Deads: 0")

        # Stats and Tools Configuration
        stats_tools_layout = BoxLayout(orientation='horizontal', size_hint=(1, 0.17), padding=dp(10), spacing=dp(5))

        # Stats
        stats_layout = BoxLayout(orientation='horizontal', spacing=dp(5))
        stats_layout.add_widget(self.result_logs_info_label)
        stats_layout.add_widget(self.result_hits_info_label)
        stats_layout.add_widget(self.result_deads_info_label)
        stats_tools_layout.add_widget(stats_layout)
        
        # Tools Dropdown
        tools_button, tools_dropdown = self.create_dropdown_menu(None, None)
        stats_tools_layout.add_widget(tools_button)

        # Stats and Tools Set
        self.layout.add_widget(stats_tools_layout)

        self.result_grid.add_widget(self.result_logs_box)
        self.result_grid.add_widget(self.result_hits_box)
        self.result_grid.add_widget(self.result_deads_box)

        # Create and return the main layout
        main_layout = FloatLayout()

        # Add watermark image
        watermark = Image(source=self.WATERMARK_PATH, allow_stretch=True, keep_ratio=False, opacity=0.65, pos_hint={'center_x': 0.5, 'center_y': 0.45}, size_hint=(0.8, 0.8))
        main_layout.add_widget(watermark)

        # Create a secondary layout to contain the existing layout
        secondary_layout = FloatLayout(size_hint=(1, 1))
        secondary_layout.add_widget(self.layout)

        # Add the secondary layout to the main layout
        main_layout.add_widget(secondary_layout)

        return main_layout

    def create_dropdown_menu(self, label, type_):
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
        dropdown = DropDown()

        def secondary_option_selected(instance):
            # Handle the selected option
            if primary_option == "Clean":
                if instance.text == "Hits":
                    self.result_hits_label.text = "Hits:\n"  
                elif instance.text == "Deads":
                    self.result_deads_label.text = "Deads:\n"  
                elif instance.text == "Logs":
                    self.result_logs_label.text = "Logs:\n"  
            
            elif primary_option == "Copy":
                if instance.text == "Hits":
                    Clipboard.copy(self.result_hits_label.text)
                elif instance.text == "Deads":
                    Clipboard.copy(self.result_deads_label.text)
                elif instance.text == "Logs":
                    Clipboard.copy(self.result_logs_label.text)

            elif primary_option == "FullScreen":
                if instance.text == "Hits":
                    self.show_full_screen(self.result_hits_label.text)
                elif instance.text == "Deads":
                    self.show_full_screen(self.result_deads_label.text)
                elif instance.text == "Logs":
                    self.show_full_screen(self.result_logs_label.text)

            elif primary_option == "Save":
                if instance.text == "Hits":
                    self.save_content(instance=self, type_="Hits")
                elif instance.text == "Deads":
                    self.save_content(instance=self, type_="Deads")
                elif instance.text == "Logs":
                    self.save_content(instance=self, type_="Logs")

            dropdown.dismiss()

        for option in ["Hits", "Deads", "Logs"]:
            btn = BorderedButton(text=option, size_hint_y=None, height=dp(40), background_color=(0, 0, 0, 1))
            btn.bind(on_release=secondary_option_selected)
            dropdown.add_widget(btn)

        return dropdown

    def button_action_and_dismiss(self, instance, text, label, type_, dropdown):
        self.button_action(text, label, type_)(instance)  # Call the button action
        dropdown.dismiss()  # Close the dropdown

    def button_action(self, text, label, type_):
        def action(instance):
            self.dropdown_option_selected(text, label, type_)
        return action

    def dropdown_option_selected(self, text, label, type_):
        if text == "Clean":
            label.text = type_ + ":\n"
        elif text == "Copy":
            Clipboard.copy(label.text)
        elif text == "FullScreen":
            self.show_full_screen(label.text)
        elif text == "Save":
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
            self.result_logs_label.text += "\n[*] Proxies Disabled!"
        else:
            # Handle other proxy type selections
            self.proxies_button.disabled = False
            self.result_logs_label.text += f"\n[*] {value} Proxies Enabled!"

    def save_content(self, type_, instance):
        """
        Display a popup with a file chooser and a save button to save the specified content type.

        :param type_: The content type to be saved (e.g., Logs, Hits, Deads).
        :param instance: The button instance triggering this method.
        """

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
        
        with open(os.path.join(path, filename), 'w') as file:
            if type_ == self.LOGS_TYPE:
                file.write(self.result_logs_label.text)
            elif type_ == self.HITS_TYPE:
                file.write(self.result_hits_label.text)
            elif type_ == self.DEADS_TYPE:
                file.write(self.result_deads_label.text)
        self.save_popup.dismiss()

    def _update_text_size(self, instance, value):
        """
        Update the width of the text widget based on the new value.
        
        :param instance: The text widget instance.
        :param value: The new size value.
        """
        instance.text_size = (value[0], None)

    def _update_text_height(self, instance, value):
        """
        Update the height of the text widget based on the texture size.
        
        :param instance: The text widget instance.
        :param value: The new size value.
        """
        instance.text_size = (value, None)
        instance.height = instance.texture_size[1]

    def load_instructions(self, instance):
        """
        Display a file chooser popup to select and load instructions.
        
        :param instance: The button instance triggering this method.
        """

        home_path = os.path.expanduser("~")
        if ":" not in home_path: home_path = "/storage/emulated/0/"
        file_chooser = FileChooserListView(path=home_path, filters=['*.txt'])
        self.choose_file_popup = Popup(title="Load Config", content=file_chooser, size_hint=(0.9, 0.9))

        file_chooser.bind(on_submit=self._load_selected_instructions)
        self.choose_file_popup.open()
        self.result_logs_label.text += f"\nLoading Config..."

    def run_custom_instructions(self, email, passwordO, proxyDict):
        """
        Processes the loaded instructions using the provided email, password, and proxy dictionary.
        
        :param email: The email to be processed.
        :param passwordO: The corresponding password.
        :param proxyDict: The proxy settings.
        :return: Result message if any.
        """

        # Ensure instructions are loaded
        if not getattr(self, 'instructions', None):
            return "\n[*] You must load instructions first!"
        
        # Initialize session
        self.my_session = retry()

        # Iterate through the instructions and process them
        for instruction in self.instructions:
            result = self.process_instruction(instruction.strip(), email, passwordO, proxyDict)
            if result:
                return result
        return None

    def load_file(self, instance):
        """Load the combo file."""
        self._setup_file_chooser("Load Combo", self._load_selected_file)
        self.result_logs_label.text += "\nLoading Combo..."

    def load_proxies(self, instance):
        """Load the proxies file."""
        self._setup_file_chooser("Load Proxies", self._load_selected_proxies)
        self.result_logs_label.text += "\nLoading Proxies..."
            
    def _load_selected_file(self, instance, selected_file, *args):
        """Process the selected combo file."""
        try:
            with open(selected_file[0], 'r') as file:
                self.combo = file.read()
                self.result_logs_label.text += f"\nCombo Loaded:\n{selected_file[0]}"
        except Exception as e:
            self.result_logs_label.text += f"\nError loading combo: {e}"
        finally:
            self.choose_file_popup.dismiss()
        
    def _load_selected_proxies(self, instance, selected_file, *args):
        """Process the selected proxies file."""
        try:
            with open(selected_file[0], 'r') as file:
                self.proxies = file.read()
                self.result_logs_label.text += f"\nProxies Loaded:\n{selected_file[0]}"
        except Exception as e:
            self.result_logs_label.text += f"\nError loading proxies: {e}"
        finally:
            self.choose_file_popup.dismiss()

    def _load_selected_instructions(self, instance, selected_file, *args):
        """Process the selected instructions file."""
        if type(selected_file) == str: selected_file = [selected_file]
        try:
            with open(selected_file[0], 'r') as file:
                self.instructions = file.read().split('\n')
                self.result_logs_label.text += f"\nInstructions Loaded:\n{selected_file[0]}"
        except Exception as e:
            self.result_logs_label.text += f"\nError loading instructions: {e}"
        finally:
            self.choose_file_popup.dismiss()

    def _setup_file_chooser(self, title, submit_callback):
        """
        Set up a file chooser with the given title and submit callback.

        :param title: Title for the popup.
        :param submit_callback: Callback function to handle the selected file.
        """
        home_path = os.path.expanduser("~")
        if ":" not in home_path:
            home_path = "/storage/emulated/0/"
        
        file_chooser = FileChooserListView(path=home_path, filters=['*.txt'])
        self.choose_file_popup = Popup(title=title, content=file_chooser, size_hint=(0.7, 0.7))
        
        file_chooser.bind(on_submit=submit_callback)
        self.choose_file_popup.open()

    def parse_proxy(self, proxy_str, proxy_type):
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

        # Split instruction into its components
        components = instruction.split('|')
        params = {key: value for key, value in (part.split('=', 1) for part in components)}

        # Check if the instruction is valid
        if 'BLOCK' not in params:
            self.result_logs_label.text += f"\nInvalid instruction: {instruction}"
            return

        # Direct to appropriate handlers based on block type
        block_type = params['BLOCK'].split('-', 1)[0]
        handler_name = f"handle_{block_type.lower()}"
        handler_method = getattr(self, handler_name, None)

        if handler_method:
            result = handler_method(params)
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
        while "<" in input_string and ">" in input_string:
            start_idx = input_string.find("<")
            end_idx = input_string.find(">")
            if start_idx != -1 and end_idx != -1:
                variable_name = input_string[start_idx + 1:end_idx].strip()
                if "REQUEST-" in variable_name:
                    variable_value = str(self.responses.get(variable_name[:-5])) if "text" in variable_name else str(self.headers.get(variable_name[:-8]))
                elif variable_name == "EMAIL":
                    variable_value = self.email
                elif variable_name == "PASSWORD":
                    variable_value = self.password
                else:
                    variable_value = str(self.variables.get(variable_name))
                
                if not variable_value:
                    self.result_logs_label.text += f"\n{variable_name} - Variable not found"
                    return
                else:
                    if encode: 
                        variable_value = quote(variable_value)
                    input_string = input_string[:start_idx] + variable_value + input_string[end_idx + 1:]
        return input_string

    def handle_result(self, params):
        """
        Handles the RESULT block type in instructions.
        
        :param params: Dictionary of parameters extracted from the instruction.
        :return: Processed result or None.
        """
        value_string = params.get('VALUE', '').strip().encode('latin1').decode('utf-8')
        variable_content = self._replace_variables(params.get('VAR', '').strip())
        category = params.get('CATEGORY', '').strip()
        return_string = params.get('RETURN', '').strip()

        # Check if the variable exists
        if not variable_content:
            return

        # Check if the value string exists in the variable content
        if value_string in variable_content:
            response_string = return_string or value_string
            return f"\nCREDENTIALS = {self.email}:{self.password} | RESPONSE = {response_string} | {category}"
        return None

    def handle_request(self, params):
        """
        Handle HTTP requests based on provided parameters.
        
        :param params: Dictionary containing parameters for the request.
        """

        block = params.get('BLOCK')
        type_ = params.get('TYPE', 'GET').upper()
        url = params.get('URL')
        headers = params.get('HEADERS')
        post_data = params.get('POST')

        if not url:
            self.result_logs_label.text += "\nURL not provided for the request"
            return
        
        url=self._replace_variables(url)

        # COnvert the headers string to a dictionary
        headers_dict = {}
        if headers:
            headers = self._replace_variables(headers)
            if headers == None:
                self.result_logs_label.text += "\nHeaders provided are invalid for the request"
                return
            headers = json.loads(headers)

        response = None
        if type_ == 'GET':
            response = self.my_session.get(url, headers=headers_dict, proxies=self.proxyDict, timeout=45, verify=False)
        elif type_ == 'POST':
            # if payload is json not must be encoded
            if post_data[0:1] == "{" or post_data[0:1] == "[":
                post_data=self._replace_variables(post_data, False)
            else:
                post_data=self._replace_variables(post_data, True)
            if post_data == None:
                return
            response = self.my_session.post(url, data=post_data, proxies=self.proxyDict, headers=headers, timeout=45, verify=False)

        if response != None:
            self.responses[block] = response.text
            self.headers[block] = response.headers
            self.cookies[block] = response.cookies
            self.result_logs_label.text += f"\n{block} - Response Code: {response.status_code}"

    def handle_save(self, params):
        """
        Save a value to a variable for later use.
        
        :param params: Dictionary containing variable name and value.
        """

        variable_name = params.get('VAR')
        value = params.get('VALUE')

        if not variable_name or value is None:
            self.result_logs_label.text += "\nVariable name or value not provided"
            return

        # Save the variable in a dictionary for later use
        self.variables[variable_name] = value
    
    def handle_find(self, params):
        """
        Find a substring between two delimiters.
        
        :param params: Dictionary containing the variable name, delimiters, and block.
        """

        block = params.get('BLOCK')
        variable_name = params.get('VAR')
        first_delimiter = params.get('FIRST')
        last_delimiter = params.get('LAST')

        if not variable_name or not variable_name:
            self.result_logs_label.text += "\nVariable name or pattern not provided"
            return
        
        if "text" in variable_name:
            variable_value = str(self.responses.get(variable_name[:-5]))
        elif "headers" in variable_name:
            variable_value = str(self.headers.get(variable_name[:-8]))
        else:
            self.result_logs_label.text += f"\nVariable {variable_name} not Found"
            return
        
        result = extract_substring(variable_value, first_delimiter, last_delimiter)
        self.variables[block] = result

        if result != "":
            self.result_logs_label.text += f"\nFIND ({variable_name}) - {result}"
            return
        else:
            self.result_logs_label.text += f"\nFIND ({variable_name}) - Not Found"
            return

    def handle_print(self, params):
        """Handle the PRINT block in the instructions."""
        variable_name = params.get('VAR')

        if not variable_name:
            self.result_logs_label.text += "\nVariable name not provided"
            return

        if "<" in variable_name:
            variable_name = self._extract_substring(variable_name, "<", ">")
            if "text" in variable_name:
                content = self.responses.get(variable_name[:-5])
            elif "headers" in variable_name:
                content = self.headers.get(variable_name[:-8])
            elif "cookies" in variable_name:
                content = self.cookies.get(variable_name[:-8])
            elif variable_name == "EMAIL":
                content = self.email
            else:
                content = self.variables.get(variable_name)

            self._print_content(variable_name, content)
        else:
            self.result_logs_label.text += f"\nVariable {variable_name} not found"

    def _print_content(self, variable_name, content):
        """Print the content of a variable in chunks."""
        if content:
            content_str = str(content)
            if len(content_str) > 1000:
                chunks = [content_str[i: i + 1000] for i in range(0, len(content_str), 1000)]
                for chunk in chunks:
                    self.result_logs_label.text += f"\nPRINT [{variable_name}] - {chunk}"
            else:
                self.result_logs_label.text += f"\nPRINT [{variable_name}] - {content_str}"
        else:
            self.result_logs_label.text += f"\nVariable {variable_name} not found or empty"

    @staticmethod
    def _extract_substring(input_string, start_delimiter, end_delimiter):
        """Extract a substring between two delimiters."""
        try:
            start = input_string.index(start_delimiter) + len(start_delimiter)
            end = input_string.index(end_delimiter, start)
            return input_string[start:end]
        except ValueError:
            return ""

    def worker(self, task_queue, selected_option):
        while not task_queue.empty():
            acc = task_queue.get()
            email, passwordO = acc.split(':')
            if self.proxies != "":
                proxy = set()
                file_lines1 = self.proxies.split('\n')
                for line1 in file_lines1:
                    proxy.add(line1.strip())
                proxyDict = self.parse_proxy(random.choice(list(proxy)), self.proxy_spinner.text.swapcase())
            else: proxyDict=None
            if selected_option == "Bees":
                self._load_selected_instructions(self, selected_file="configs/bees.txt")
                result = self.run_custom_instructions(email, passwordO, proxyDict)
            elif selected_option == "Custom":
                result = self.run_custom_instructions(email, passwordO, proxyDict)
            if not result:
                self.result_logs_label.text += f"\n[*] Combo Finished!"
                return
            elif "You must load instructions first!" in result:
                self.result_logs_label.text += f"\n[*] You must load instructions first!"
                return
            elif result:
                self.update_gui(result)
                progress = (self.progreso + 1) / self.total_instructions * 100
                self.progress_bar.value += progress
            self.check_times.append(time.time())
            self.update_cpm()
            self.worker_threads_running -= 1  # Decrement the count of running threads
            task_queue.task_done()
        
    def update_cpm(self, dt=None):  # Dt is the delta time between calls
        current_time = time.time()
        # Remove all the times that are older than 60 seconds
        self.check_times = [t for t in self.check_times if current_time - t < 60]
        cpm = len(self.check_times)
        self.update_info_label(self.result_logs_info_label, f"CPM: {cpm}")

    def update_info_label(self, label, info_text):
        label.text = info_text

    def check_threads_finished(self, dt):
        if self.worker_threads_running == 0:
            print("Threads Finished")
        if self.progress_bar.value == 100 and self.impreso == False:
            self.impreso = True
            self.state_label.text = "State: Sleeping"
            self.result_logs_label.text += f"\n[*] Combo Finished!"

    def update_gui(self, result):
        def update(dt):
            if result == None:
                return
            if "HIT" in result:
                self.result_hits_label.text += result
                self.hits_count += 1
                self.update_info_label(self.result_hits_info_label, f"Hits: {self.hits_count}")
            elif "DEAD" in result:
                self.result_deads_label.text += result
                self.deads_count += 1
                self.update_info_label(self.result_deads_info_label, f"Deads: {self.deads_count}")
            else:
                self.result_logs_label.text += result
        Clock.schedule_once(update)

    def run_file(self, instance):
        Clock.schedule_interval(self.update_cpm, 1)
        self.check_times = []
        self.deads_count = 0
        self.hits_count = 0
        self.impreso = False
        self.state_label.text = "State: Running"
        self.progress_bar.value = 0
        selected_option = self.options_spinner.text

        if self.proxies == "" and self.proxies_button.disabled == False:
            self.result_logs_label.text += f"\n[*] You must load Proxies!"
            self.state_label.text = "State: Sleeping"
            return

        if self.combo == "":
            self.state_label.text = "State: Sleeping"
            self.result_logs_label.text += f"\n[*] You must load a Combo!"
            return

        try: self.threads = int(self.threads_input.text)
        except ValueError:
            self.state_label.text = "State: Sleeping"
            self.result_logs_label.text += f"\n[*] Invalid Threads Number!"
            return

        accsLista = []
        acssLines = self.combo.split('\n')
        for line in acssLines:
            accsLista.append(line.strip())

        self.result_queue = Queue()

        self.worker_threads_running = 0

        self.task_queue = Queue()
        for acc in acssLines:
            self.task_queue.put(acc)
        self.total_instructions = self.task_queue.qsize()
        proxy = set()
        file_lines1 = self.proxies.split('\n')
        for line1 in file_lines1:
            proxy.add(line1.strip())

        # Start the worker threads
        for _ in range(self.threads):
            self.worker_threads_running += 1  # Increment the count of running threads
            thread = Thread(target=self.worker, args=(self.task_queue, selected_option))
            thread.start()

        Clock.schedule_interval(self.check_threads_finished, 1)

        return

if __name__ == '__main__':
    BulletApp().run()
