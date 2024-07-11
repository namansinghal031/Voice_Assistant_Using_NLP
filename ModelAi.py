import tkinter as tk
from tkinter import ttk  # For combobox
from threading import Thread
import pyttsx3
import speech_recognition as sr
import datetime
import wikipedia
import webbrowser
import requests
import mysql.connector
import json
from PIL import Image, ImageTk, ImageOps

# Ensure the MySQL server is running and the specified database and table(s) exist.
# Database connection setup
try:
    cnx = mysql.connector.connect(host='localhost', user='root', password='', database='Voice_assist')
    cursor = cnx.cursor()
    print("Database connection successful.")
except mysql.connector.Error as err:
    print(f"Failed to connect to database: {err}")


def initialize_engine(voice_preference='male'):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    if voice_preference == 'female':
        engine.setProperty('voice', voices[1].id)  # Assuming the second voice in the list is female
    else:
        engine.setProperty('voice', voices[0].id)  # Default to the first voice (male)
    return engine


def speak(engine, text, response_area=None, gui_mode=False):
    if gui_mode and response_area:
        response_area.insert(tk.END, "Emory:" + text + "\n")
        response_area.see(tk.END)  # Autoscroll to the latest entry
    engine.say(text)
    engine.runAndWait()


def listen(engine, response_area=None, gui_mode=False):
    r = sr.Recognizer()
    with sr.Microphone() as source:
        if gui_mode and response_area:
            response_area.insert(tk.END, "Listening...\n")
            response_area.see(tk.END)  # Autoscroll to the latest entry
        audio = r.listen(source)
        try:
            command = r.recognize_google(audio)
            if gui_mode and response_area:
                response_area.insert(tk.END, f"You: {command}\n")
                response_area.see(tk.END)  # Autoscroll to the latest entry
        except Exception as e:
            if gui_mode and response_area:
                response_area.insert(tk.END, "I didn't get that. Try typing the command.\n")
                response_area.see(tk.END)  # Autoscroll to the latest entry
            command = None
    return command


def get_current_location_and_open_in_maps():
    try:
        response = requests.get('https://ipinfo.io/json')
        data = response.json()
        location = data['loc']
        webbrowser.open(f"https://www.google.com/maps/?q={location}")
        return f"Opened your current location in Google Maps: {location}"
    except Exception as e:
        return "Failed to fetch or open current location."


def search_wikipedia(query):
    try:
        results = wikipedia.summary(query, sentences=2)
        return "According to Wikipedia, " + results
    except wikipedia.exceptions.PageError:
        return "Couldn't find a Wikipedia page for that."
    except wikipedia.exceptions.DisambiguationError as e:
        return f"Your query could refer to multiple items: {e.options[0]}, {e.options[1]}, etc."
    except Exception as e:
        return "Failed to search Wikipedia due to an error."


def create_conversation_table(table_name):
    try:
        create_table_query = f"""
	        CREATE TABLE IF NOT EXISTS `{table_name}` (
	            ID INT AUTO_INCREMENT PRIMARY KEY,
	            Date_Time DATETIME NOT NULL,
	            UserCommand TEXT,
	            JarvisResponse TEXT
	        )
	        """
        cursor.execute(create_table_query)
        cnx.commit()
        print(f"Table `{table_name}` created successfully.")
    except mysql.connector.Error as err:
        print(f"Failed to create table `{table_name}`: {err}")


def log_conversation(user_command, jarvis_response):
    # This time, instead of creating a new table for each day,
    # we log into the most recent table or create one if none exists.
    table_name = get_most_recent_conversation_table()
    if not table_name:  # If no table exists, create a new one
        table_name = "Conversation_" + datetime.datetime.now().strftime("%Y%m%d")
        create_conversation_table(table_name)

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        insert_query = f"INSERT INTO `{table_name}` (Date_Time, UserCommand, JarvisResponse) VALUES (%s, %s, %s)"
        cursor.execute(insert_query, (now, user_command, jarvis_response))
        cnx.commit()
    except mysql.connector.Error as err:
        print(f"Failed to log conversation to table `{table_name}`:", err)


def get_most_recent_conversation_table():
    """
    Retrieves the name of the most recently created conversation table.
    """
    query = """
	    SELECT table_name FROM information_schema.tables
	    WHERE table_schema = 'prateek12' AND table_name LIKE 'Conversation_%'
	    ORDER BY create_time DESC LIMIT 1;
	    """
    cursor.execute(query)
    r = cursor.fetchone()
    print(r)
    query1 = f"SELECT * from {r[0]};"
    try:
        cursor.execute(query1)
        result = cursor.fetchall()
        if result:
            for i in result:
                print(i, end='\n')
            return result
        else:
            return None
    except mysql.connector.Error as err:
        print(f"Failed to fetch the most recent conversation table: {err}")
        return None


def save_state(user_id, state):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    state_json = json.dumps(state)
    try:
        cursor.execute("REPLACE INTO UserState (UserID, State, LastUpdated) VALUES (%s, %s, %s)",
                       (user_id, state_json, now))
        cnx.commit()
    except Exception as e:
        print("Failed to save state:", e)


def retrieve_and_continue_conversation_gui():
    """
    GUI version to retrieve the last conversation from the most recent table and display it.
    """
    table_name = get_most_recent_conversation_table()
    if not table_name:
        response_area.insert(tk.END, "No conversation history found.\n")
        response_area.see(tk.END)
        return

    try:
        query = f"SELECT * FROM `{table_name}` ORDER BY ID DESC LIMIT 1"
        cursor.execute(query)
        last_conversation = cursor.fetchone()
        if last_conversation:
            response_area.insert(tk.END,
                                 f"Last conversation from {table_name}:\nYou: {last_conversation[2]}\nEmory: {last_conversation[3]}\n")
            response_area.see(tk.END)
        else:
            response_area.insert(tk.END, "No conversation history found in the most recent table.\n")
            response_area.see(tk.END)
    except mysql.connector.Error as err:
        response_area.insert(tk.END, f"Failed to retrieve last conversation: {err}\n")


def handle_command(engine, command, user_id, response_area=None, gui_mode=False):
    response = ""
    command_lower = command.lower()

    if 'hello' in command_lower or 'hey' in command_lower or 'hi' in command_lower:
        response = "Hello! How can I assist you today?"
    elif 'your name' in command_lower or 'who are you' in command_lower:
        response = "I am Emory, your personal assistant."
    elif 'wikipedia' in command_lower or 'what is' in command_lower or 'who is' in command_lower:
        speak(engine, "Searching Wikipedia...", response_area, gui_mode)
        query = command_lower.replace("wikipedia", "").replace("search", "").strip()
        response = search_wikipedia(query)
    elif 'open youtube' in command_lower:
        webbrowser.open("https://www.youtube.com")
        response = "Opening YouTube."
    elif 'open google' in command_lower:
        webbrowser.open("https://www.google.com")
        response = "Opening Google."
    elif 'open facebook' in command_lower:
        webbrowser.open('https://www.facebook.com')
        response = "Opening Facebook."
    elif 'open instagram' in command_lower or 'instagram' in command_lower:
        webbrowser.open('https://www.instagram.com')
        response = "Opening Instagram."
    elif 'open maps' in command_lower or 'my location' in command_lower or 'show me where i am' in command_lower:
        response = get_current_location_and_open_in_maps()
    elif 'the time' in command_lower:
        strTime = datetime.datetime.now().strftime("%H:%M:%S")
        response = f"The time is {strTime}"
    elif 'open aums' in command_lower:
        webbrowser.open(
            "https://aumscn.amrita.edu/cas/login?service=https%3A%2F%2Faumscn.amrita.edu%2Faums%2FJsp%2FCore_Common%2Findex.jsp")
        response = "opening AUMS."
    elif 'open amazon' in command_lower:
        webbrowser.open(
            "https://www.google.com/url?sa=t&source=web&rct=j&opi=89978449&url=https://www.amazon.in/&ved=2ahUKEwjuooXFp5mFAxX5b2wGHVelB5MQFnoECAgQAQ&usg=AOvVaw11iWiBdQ4J9QF64so00kjl")
        response = "openning amazon"

    # Add more commands as needed

    if response:
        speak(engine, response, response_area, gui_mode)
        if user_id is not None:  # Assuming a valid user_id indicates a need to log conversations
            log_conversation(command, response)

    # Add other command handling logic here...


def start_listening_thread(engine, user_id, response_area):
    def callback():
        command = listen(engine, response_area, True)
        if command:
            handle_command(engine, command, user_id, response_area, True)

    thread = Thread(target=callback)
    thread.start()


def handle_text_command():
    command = text_input.get()
    if command:
        response_area.insert(tk.END, f"You: {command}\n")
        response_area.see(tk.END)  # Scroll to the latest entry
        handle_command(engine, command, user_id, response_area, True)
        text_input.delete(0, tk.END)


def change_voice():
    global engine
    preference = voice_preference_combobox.get().lower()
    engine = initialize_engine(preference)
    speak(engine, f"Voice changed to {preference}.", None, False)


def create_gui():
    global text_input, response_area, engine, user_id, voice_preference_combobox
    engine = initialize_engine()
    user_id = 1

    root = tk.Tk()
    root.title("Emory")
    root.geometry('600x500')  # Adjusted window size for image and layout

    # Load and display an image
    image = Image.open("Speaking-Transparent.png")
    image = ImageOps.exif_transpose(image)  # Correct orientation based on EXIF data
    image = image.resize((200, 200), Image.Resampling.LANCZOS)  # Updated resizing method
    photo = ImageTk.PhotoImage(image)
    label = tk.Label(root, image=photo)
    label.image = photo  # Keep a reference!
    label.pack()

    frame = tk.Frame(root)
    frame.pack(pady=10)

    text_input = tk.Entry(frame, width=50)
    text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    send_button = tk.Button(frame, text="Send", command=handle_text_command)
    send_button.pack(side=tk.RIGHT)

    response_frame = tk.Frame(root)
    response_frame.pack(fill=tk.BOTH, expand=True)

    response_area = tk.Text(response_frame, height=15, state='normal')
    response_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(response_frame, command=response_area.yview)
    scrollbar.pack(side=tk.RIGHT, fill='y')

    response_area['yscrollcommand'] = scrollbar.set

    voice_preference_frame = tk.Frame(root)
    voice_preference_frame.pack(pady=10)

    voice_preference_combobox = ttk.Combobox(root, values=["Male", "Female"], state="readonly")
    voice_preference_combobox.pack()
    voice_preference_combobox.set("Male")  # Default value

    def change_voice():
        preference = voice_preference_combobox.get().lower()
        initialize_engine(preference)
        speak(engine, f"Voice changed to {preference}.", None, False)

    change_voice_button = tk.Button(root, text="Change Voice", command=change_voice)
    change_voice_button.pack(pady=5)

    listen_button = tk.Button(root, text="Start Listening",
                              command=lambda: start_listening_thread(engine, user_id, response_area))
    listen_button.pack(pady=10)

    retrieve_conv_button = tk.Button(root, text="Retrieve Last Conversation",
                                     command=lambda: get_most_recent_conversation_table())
    retrieve_conv_button.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    create_gui()
